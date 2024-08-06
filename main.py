import os
import time
from datetime import datetime, timedelta
import sqlite3
import sys
import re
import shutil
import random
import json
import sys

import lchalk


class SQLError(Exception):
    def __init__(self, message):
        # Call the base class constructor with the message
        super().__init__("Erreur SQL : " + message)


class BadInput(Exception):
    def __init__(self, message):
        # Call the base class constructor with the message
        super().__init__("Mauvaise entrée : " + message)


path_to_database = "/home/sybilvane/Documents/Baze podataka/temps4.1"

# PATH FOR TESTING PURPOSES !
# path_to_database = "/home/sybilvane/Desktop/testdb"

commands = [("help", "", "Faire une liste de commands."),
            ("list", "", "Faire une liste d'activités et de catégories."),
            ("backup", "", "Faire une sauvegarde sur le bureau."),
            ("add act", "[nom] [catégorie] [description]", "Ajouter une nouvelle activité."),
            ("add mand act", "[description]", "Ajouter une nouvelle activité obligatoire."),
            ("add obj", "[activités/catégories...] [temps cibles...]", "Ajouter nouveau objectif."),
            ("add mand obj", "[activités obligatoires...]", "Ajouter nouveau objectif obligatoire."),
            ("clear", "", "Effacer tout."),
            ("exit", "", "Sortir de l'application."),
            ("stats", "", "Afficher les statistiques. On peux ajouter des drapeaux -wmyatc."),
            ("c", "[nom d'activité obligatoire]", "Signaler qu'un activité obligatoire est fait."),
            ("export", "[json | psv]", "Exporter comme un json ou psv."),
            ("motivation", "", "Générer une citation de motivation aléatoire."),
            ("trend", "", "Calculer le temps projeté passé à travailler jusqu'à la fin de la semaine.")]

prs_filename = "tempus8_prs.txt"

def stringify_month(month):
    if month == 1:
        return "janvier"
    elif month == 2:
        return "février"
    elif month == 3:
        return "mars"
    elif month == 4:
        return "avril"
    elif month == 5:
        return "mai"
    elif month == 6:
        return "juin"
    elif month == 7:
        return "juillet"
    elif month == 8:
        return "août"
    elif month == 9:
        return "septembre"
    elif month == 10:
        return "octobre"
    elif month == 11:
        return "novembre"
    elif month == 12:
        return "décembre"


def get_lazarus_day():
    today = datetime.today().now()

    if today.hour < 5:
        today = today - timedelta(1)

    return today


def format_date(date_obj):
    return str(date_obj.day) + " " + stringify_month(date_obj.month) + " " + str(date_obj.year)


def draw_title():
    os.system("clear")
    new_string = ("""

 __                                          ______      ______ 
|  |_ .-----..--------..-----..--.--..-----.|  __  |    |      |
|   _||  -__||        ||  _  ||  |  ||__ --||  __  | __ |  --  |
|____||_____||__|__|__||   __| \___/ |_____||______||__||______|
                       |__|                                     

""")
    new_string += format_date(get_lazarus_day())
    return new_string


def get_today_worked():
    search_date = get_lazarus_day().strftime("%Y-%m-%d")

    con = sqlite3.connect(path_to_database)
    cur = con.cursor()
    cur.execute("SELECT SUM(WorkTime) FROM Entries WHERE WorkDate = ?;", (search_date,))
    value = cur.fetchone()[0]
    con.close()
    if value is None:
        return 0
    return value


def get_this_week_worked():
    ending_day = get_lazarus_day()
    start_day = get_lazarus_day()
    delta = start_day.weekday()
    start_day = start_day - timedelta(delta)

    start_day = start_day.strftime("%Y-%m-%d")
    ending_day = ending_day.strftime("%Y-%m-%d")

    con = sqlite3.connect(path_to_database)
    cur = con.cursor()
    cur.execute("SELECT SUM(WorkTime) FROM Entries WHERE WorkDate >= ? AND WorkDate <= ?", (start_day, ending_day))
    value = cur.fetchone()[0]
    con.close()
    if value is None:
        return 0
    return value


def pipefy(number, color):
    # number is in minutes
    pipe_string = ""
    if color == "cyan":
        number_of_pipes = number // 30
        if number_of_pipes > 20:
            number_of_pipes = 20

        for i in range(number_of_pipes):
            pipe_string += "|"

        if number_of_pipes >= 20:
            pipe_string = lchalk.colorize(pipe_string, "green")
            return pipe_string

        pipe_string = lchalk.colorize(pipe_string, color)
        for i in range(20 - number_of_pipes):
            pipe_string += "|"
        return pipe_string
    elif color == "magenta":
        con = sqlite3.connect(path_to_database)
        cur = con.cursor()
        cur.execute(
            "SELECT SUM(TargetTime) FROM DailyGoalAux JOIN DailyGoal ON DailyGoalAux.DailyGoalID = DailyGoal.DailyGoalID  WHERE DailyGoalDate = (SELECT DailyGoalDate FROM DailyGoal ORDER BY DailyGoalID DESC LIMIT 1) ORDER BY TargetTime DESC;")
        goal_time_this_week = cur.fetchone()[0]
        con.close()
        if goal_time_this_week is None:
            return lchalk.colorize("aucun objectif !", "red")
        else:
            goal_time_this_week *= 7
        worked_this_week = get_this_week_worked()

        pipes_done = round((worked_this_week / goal_time_this_week) * 20)
        for i in range(20):
            if i < pipes_done:
                pipe_string += lchalk.colorize("|", "magenta")
            else:
                pipe_string += "|"
        return pipe_string


def variable_spacing(number):
    if number == 0:
        return 13 - 1

    i = 0
    while number != 0:
        i += 1
        number //= 10

    return 13 - i


def write_weekly_pbs(percentage):
    if percentage == 0:
        return lchalk.colorize(" HORRIBLE ", "black", "red")
    if percentage < 20:
        return lchalk.colorize(" MAUVAIS ", "black", "red")
    if percentage < 40:
        return lchalk.colorize(" MOYEN ", "black", "yellow")
    if percentage < 60:
        return lchalk.colorize(" BON ", "black", "green")
    return lchalk.colorize(" EXCELLENT ", "black", "cyan")


def get_name_and_worktime(item):
    con = sqlite3.connect(path_to_database)
    cur = con.cursor()
    search_date = get_lazarus_day().strftime("%Y-%m-%d")
    name = ""
    time = 0

    if item[2] == 1:
        # it's a category
        cur.execute(
            "SELECT Name FROM Category WHERE SubCategoryID = ?",
            (item[0],))
        name = cur.fetchone()[0]
        cur.execute(
            "SELECT SUM(WorkTime) FROM Entries JOIN Activities ON Activities.ActivityID = Entries.ActivityID WHERE WorkDate = ? AND SubCategoryID = ?",
            (search_date, item[0],))
        value = cur.fetchone()
        if value[0] is not None:
            time = value[0]
    else:
        # it's an activity
        cur.execute(
            "SELECT Name FROM Activities WHERE ActivityID = ?",
            (item[0],))
        name = cur.fetchone()[0]
        cur.execute(
            "SELECT SUM(WorkTime) FROM Entries WHERE WorkDate = ? AND ActivityID = ?",
            (search_date, item[0]))
        value = cur.fetchone()
        if value is not None:
            time = value[0]

    name = " • " + name
    con.close()

    return name, time


def get_name_and_status(id):
    name = ""
    status = ""
    search_date = get_lazarus_day().strftime("%Y-%m-%d")

    con = sqlite3.connect(path_to_database)
    cur = con.cursor()
    cur.execute("SELECT Description FROM MandatoryActivity WHERE MandatoryActivityID = ?", (id,))
    name = cur.fetchall()[0][0]

    cur.execute("SELECT * FROM MandatoryEntries WHERE MandatoryEntriesDate = ? AND MandatoryActivityID = ?",
                (search_date, id))
    value = cur.fetchall()
    if not value:
        status = "pas fait"
    else:
        status = "fait"

    con.close()
    return name, status


def get_weekly_pbs():
    today = datetime.today().now()
    days_since_monday = today.weekday()  # Monday is 0, Sunday is 6
    if days_since_monday == 0 and today.hour < 5:
        days_since_monday = 7
    hrs_since_5AM_MON = (days_since_monday * 24 + today.hour + today.minute / 60) - 5
    hrs_awake = days_since_monday * 16

    if hrs_since_5AM_MON % 24 <= 16:
        hrs_awake += hrs_since_5AM_MON % 24
    elif hrs_since_5AM_MON % 24 > 16:
        hrs_awake += 16

    if hrs_awake == 0:
        return 0
    return ((get_this_week_worked() / 60) / hrs_awake) * 100


def print_goals():
    search_date = get_lazarus_day().strftime("%Y-%m-%d")

    con = sqlite3.connect(path_to_database)
    cur = con.cursor()

    output = ""

    cur.execute(
        "SELECT Name, SUM(WorkTime) AS TotalTime FROM Activities JOIN Entries ON Activities.ActivityID = Entries.ActivityID WHERE WorkDate = ? GROUP BY Name ORDER BY TotalTime DESC",
        (search_date,))
    value = cur.fetchall()
    if not value:
        output += lchalk.colorize("\tRIEN\n", "yellow")

    for row in value:
        print("\t{:<38} {:>3}".format(lchalk.colorize(str(row[0]), "cyan"), row[1]))

    print(output)

    global delim
    print(delim + "\n")

    cur.execute(
        "SELECT ActivityCategoryID, TargetTime, IsCategory FROM DailyGoalAux WHERE DailyGoalID = (SELECT DailyGoalID FROM DailyGoal ORDER BY DailyGoalID DESC LIMIT 1) ORDER BY TargetTime DESC;")
    value = cur.fetchall()
    if not value:
        lchalk.colorize_and_print(" AUCUN OBJECTIF.", "red")

    for item in value:
        data = get_name_and_worktime(item)
        if data[1] is None:
            time = 0
        else:
            time = data[1]

        if int(time) >= item[1]:
            time = lchalk.colorize(time, "green")
        else:
            time = lchalk.colorize(time, "cyan")

        print("{:<54} {:>10}".format(data[0], time + "/" + str(item[1])))

    if value:
        print("")

    cur.execute(
        "SELECT MandatoryActivityID FROM MandatoryGoalAux WHERE MandatoryGoalID = (SELECT MandatoryGoalID FROM MandatoryGoal ORDER BY MandatoryGoalID DESC LIMIT 1)")
    value = cur.fetchall()
    if value is None:
        lchalk.colorize_and_print("AUCUN OBJECTIF OBLIGATOIRE.", "red")

    for item in value:
        data = get_name_and_status(item[0])
        name = data[0]
        status = data[1]
        if status == "fait":
            status = lchalk.colorize(status, "green")
        else:
            status = lchalk.colorize(status, "red")
        print("{:<54} {:>10}".format(" ↣ " + name, status))

    print("\n" + delim + "\n")
    con.close()


def refresh():
    global delim
    worked_today = get_today_worked()
    worked_this_week = get_this_week_worked()

    lchalk.colorize_and_print(draw_title(), title_color)
    print("{:<22} {:>10} {:>{width}} {}".format("Aujourd'hui :",
                                                lchalk.colorize(worked_today, "cyan"),
                                                "",
                                                pipefy(worked_today, "cyan"),
                                                width=variable_spacing(worked_today)))
    print("{:<22} {:<10} {:>{width}} {}".format("Cette semaine :",
                                                lchalk.colorize(worked_this_week, "magenta"),
                                                "",
                                                pipefy(worked_this_week, "magenta"),
                                                width=variable_spacing(worked_this_week)))
    print("{:<22} {:<10.2f} {:>3} {}".format("%BS (semaine) :",
                                          get_weekly_pbs(),
                                          "",
                                          write_weekly_pbs(get_weekly_pbs())))
    print("\n")
    update_prs(get_today_worked(), get_this_week_worked())
    prs = get_prs()
    print("Record personnel quotidien : " + lchalk.colorize(str(prs[0]), "cyan"))
    print("Record personnel hebdomadaire : " + lchalk.colorize(str(prs[1]), "magenta"))
    print()

    delim = ""
    for i in range(64):
        delim += "∙"
    delim = lchalk.colorize(delim, title_color)
    print(delim + "\n")
    print_goals()


def update_prs(today, this_week):
    current_prs = get_prs()
    new_prs = current_prs.copy()
    if current_prs[0] < today:
        new_prs[0] = today
    if current_prs[1] < this_week:
        new_prs[1] = this_week

    if current_prs[0] != new_prs[0] or current_prs[1] != new_prs[1]:
        with open(prs_filename, 'w') as file:
            content = "daily_best: "
            content += str(new_prs[0])
            content += "\nweekly_best: "
            content += str(new_prs[1])
            file.write(content)


def get_activity_id(name):
    con = sqlite3.connect(path_to_database)
    cur = con.cursor()
    cur.execute("SELECT ActivityID FROM Activities WHERE LOWER(Name) = ?", (name.lower(),))
    value = cur.fetchall()
    con.close()
    if value:
        return value[0][0]
    return None


def get_category_id(name):
    con = sqlite3.connect(path_to_database)
    cur = con.cursor()
    cur.execute("SELECT SubCategoryID FROM Category WHERE LOWER(Name) = ?", (name.lower(),))
    value = cur.fetchall()
    con.close()
    if value:
        return value[0][0]
    return None


def get_prs():
    con = sqlite3.connect(path_to_database)
    try:
        # format:
        # daily_best: int
        # weekly_best: int

        if os.path.exists(prs_filename):
            with open(prs_filename, 'r') as file:
                content = file.read()
                prs = []
                for row in content.split('\n'):
                    prs.append(int(row.split(' ')[1]))
            return prs
        else:
            with open(prs_filename, 'w') as file:
                content = "daily_best: "
                cur = con.cursor()
                cur.execute(
                    "SELECT SUM(WorkTime), WorkDate FROM Entries GROUP BY WorkDate ORDER BY SUM(WorkTime) DESC LIMIT 1;")
                value = cur.fetchall()
                if not value:
                    value = "0"
                else:
                    value = str(value[0][0])

                content += value
                content += "\nweekly_best: "

                current_weekly_max = get_this_week_worked()
                cur.execute("SELECT WorkDate FROM Entries ORDER BY WorkDate ASC LIMIT 1")
                value = cur.fetchall()
                if not value:
                    content += "0"
                else:
                    earliest_date = str(value[0][0])
                    monday = get_lazarus_day()
                    sunday = get_lazarus_day()
                    monday = monday - timedelta(monday.weekday())
                    while True:
                        if sunday.strftime("%Y-%m-%d") != get_lazarus_day().strftime(
                                "%Y-%m-%d") and sunday.weekday() != 6:
                            while sunday.weekday() != 6:
                                sunday = sunday + timedelta(1)

                        start_day = monday.strftime("%Y-%m-%d")
                        ending_day = sunday.strftime("%Y-%m-%d")

                        cur.execute("SELECT SUM(WorkTime) FROM Entries WHERE WorkDate >= ? AND WorkDate <= ?",
                                    (start_day, ending_day))
                        value = cur.fetchone()[0]
                        if value is not None:
                            if int(value) > current_weekly_max:
                                current_weekly_max = int(value)

                        if datetime.strptime(start_day, "%Y-%m-%d") <= datetime.strptime(earliest_date, "%Y-%m-%d"):
                            break

                        monday = monday - timedelta(7)
                        sunday = sunday - timedelta(7)

                    content += str(current_weekly_max)

                con.close()
                file.write(content)
            return get_prs()
    except:
        print(lchalk.colorize("Erreur inattendue : pas pu créer le fichier " + prs_filename + ".", "red"))
        os.remove(prs_filename)
        con.close()
        return [-1, -1]


# returns True if executed successfully
def insert_new_entry(time, activity, isYesterday):
    try:
        if time > 1440 or time <= 0:
            raise BadInput("Champ pour le temps n'est pas bon.")

        insertion_date = get_lazarus_day()
        if isYesterday:
            insertion_date = insertion_date - timedelta(1)
        insertion_date = insertion_date.strftime("%Y-%m-%d")

        con = sqlite3.connect(path_to_database)
        cur = con.cursor()
        cur.execute("SELECT EntriesID FROM Entries ORDER BY EntriesID DESC LIMIT 1")
        next_id = cur.fetchall()
        if not next_id:
            next_id = 1
        else:
            next_id = int(next_id[0][0]) + 1

        activity_id = get_activity_id(activity)
        if activity_id is None:
            raise BadInput("l'activité n'existe pas.")

        # EntriesID, ActivityID, WorkTime, WorkDate
        cur.execute("INSERT INTO Entries VALUES(?, ?, ?, ?)", (next_id, activity_id, time, insertion_date))
        con.commit()
        con.close()

        return True
    except BadInput as e:
        lchalk.colorize_and_print(str(e), "yellow")
        return False
    except Exception as e:
        lchalk.colorize_and_print(str(e), "red")
        return False


def insert_activity(name, category, description):
    try:
        if name is None or category is None:
            raise BadInput("l'activité n'existe pas.")

        flag = True
        for i in range(len(name)):
            if name[i] != ' ':
                flag = False
                break

        if flag:
            raise BadInput("mauvais nom.")

        con = sqlite3.connect(path_to_database)
        cur = con.cursor()
        cur.execute("SELECT ActivityID FROM Activities ORDER BY ActivityID DESC LIMIT 1")
        next_id = cur.fetchall()
        if not next_id:
            next_id = 1
        else:
            next_id = int(next_id[0][0]) + 1

        cur.execute("SELECT SubCategoryID FROM Category WHERE LOWER(Name) = ?", (category.lower(),))
        category_id = cur.fetchall()
        if not category_id:
            category_id = 1
        else:
            category_id = category_id[0][0]

        cur.execute("INSERT INTO Activities VALUES(?, ?, ?, ?)", (next_id, name, category_id, description))

        con.commit()
        con.close()

        return True
    except BadInput as e:
        lchalk.colorize_and_print(str(e), "yellow")
        return False
    except SQLError as e:
        lchalk.colorize_and_print(str(e), "yellow")
        return False


def insert_mand_activity(name):
    try:
        if name is None:
            raise BadInput("l'activité n'existe pas.")

        flag = True
        for i in range(len(name)):
            if name[i] != ' ':
                flag = False
                break

        if flag:
            raise BadInput("mauvais nom.")

        con = sqlite3.connect(path_to_database)
        cur = con.cursor()
        cur.execute("SELECT MandatoryActivityID FROM MandatoryActivity ORDER BY MandatoryActivityID DESC LIMIT 1")
        next_id = cur.fetchall()
        if not next_id:
            next_id = 1
        else:
            next_id = int(next_id[0][0]) + 1

        cur.execute("INSERT INTO MandatoryActivity VALUES(?, ?)", (next_id, name))
        con.commit()
        con.close()
        return True
    except BadInput as e:
        lchalk.colorize_and_print(str(e), "yellow")
        return False
    except SQLError as e:
        lchalk.colorize_and_print(str(e), "yellow")
        return False


def mand_act_exists(name):
    con = sqlite3.connect(path_to_database)
    cur = con.cursor()
    cur.execute("SELECT * FROM MandatoryActivity WHERE Description = ?", (name,))
    value = cur.fetchall()
    if not value:
        return False
    return True


def complete_mand_act(name):
    try:
        if name is None or not mand_act_exists(name):
            raise BadInput("l'activité n'existe pas.")

        con = sqlite3.connect(path_to_database)
        cur = con.cursor()
        cur.execute("SELECT MandatoryEntriesID FROM MandatoryEntries ORDER BY MandatoryEntriesID DESC LIMIT 1")
        next_id = cur.fetchall()
        if not next_id:
            next_id = 1
        else:
            next_id = int(next_id[0][0]) + 1

        cur.execute("SELECT MandatoryActivityID FROM MandatoryActivity WHERE LOWER(Description) = ?", (name.lower(),))
        mand_act_id = cur.fetchall()
        if not mand_act_id:
            mand_act_id = 1
        else:
            mand_act_id = mand_act_id[0][0]

        insertion_date = get_lazarus_day().strftime("%Y-%m-%d")
        cur.execute("SELECT * FROM MandatoryEntries WHERE MandatoryActivityID = ? AND MandatoryEntriesDate = ?",
                    (mand_act_id, insertion_date))
        result = cur.fetchall()
        if result:
            raise BadInput("déjà complété.")

        cur.execute("INSERT INTO MandatoryEntries VALUES(?, ?, ?)", (next_id, mand_act_id,
                                                                     insertion_date))
        con.commit()
        con.close()
        return True
    except BadInput as e:
        lchalk.colorize_and_print(str(e), "yellow")
        return False
    except SQLError as e:
        lchalk.colorize_and_print(str(e), "yellow")
        return False


def list_everything():
    try:
        con = sqlite3.connect(path_to_database)
        cur = con.cursor()
        cur.execute("SELECT * FROM Category")
        categories = cur.fetchall()
        if not categories:
            raise SQLError("la table ’Category’ est vide !")

        for row in categories:
            lchalk.colorize_and_print(row[1], "cyan")
            print()
            cur.execute("SELECT * FROM Activities WHERE SubCategoryID = ?", (row[0],))
            activities = cur.fetchall()

            for i in range(len(activities)):
                lchalk.colorize_and_print("\t" + str(activities[i][1]) + "\n", "magenta")

                limit = 64
                current_line = 0
                output = "\t"
                for j in range(len(activities[i][3])):
                    current_char = activities[i][3][j]
                    output += current_char

                    if current_char == ' ' and current_line + 7 > limit:
                        output += "\n\t"
                        current_line = 0
                    else:
                        current_line += 1

                if output != "":
                    print(output + "\n\n")
                else:
                    print("\n")

        con.close()
        return True
    except BadInput as e:
        lchalk.colorize_and_print(str(e), "yellow")
        return False
    except SQLError as e:
        lchalk.colorize_and_print(str(e), "yellow")
        return False


def write_to_export_file(option, value, filename):
    prefix = ""
    if option == "psv":
        prefix = "PSV Export "
    else:
        prefix = "JSON Export "

    dir_name = prefix + str(int(time.time())) + ", Tempus"
    export_path = os.path.join(os.path.expanduser("~"), "Desktop/" + dir_name)
    os.makedirs(export_path, exist_ok=True)

    column_names = {
        "Category": ["SubCategoryID", "Name"],
        "Activities": ["ActivityID", "Name", "SubCategoryID", "Description"],
        "MandatoryActivity": ["MandatoryActivityID", "Description"],
        "MandatoryGoal": ["MandatoryGoalID", "MandatoryGoalDate"],
        "MandatoryGoalAux": ["MandatoryGoalAuxID", "MandatoryGoalID", "MandatoryActivityID"],
        "MandatoryEntries": ["MandatoryEntriesID", "MandatoryActivityID", "MandatoryEntriesDate"],
        "DailyGoal": ["DailyGoalID", "DailyGoalDate"],
        "DailyGoalAux": ["DailyGoalAuxID", "DailyGoalID", "ActivityCategoryID", "TargetTime", "IsCategory"],
        "Entries": ["EntriesID", "ActivityID", "WorkTime", "WorkDate"]
    }

    extension = ""
    if option == "psv":
        extension += ".psv"
    else:
        extension += ".json"

    with open(export_path + "/" + filename + extension, "w") as file:
        if option == "psv" and value:
            for row in value:
                output = ""
                for j in range(len(row)):
                    output += str(row[j])
                    if j != len(row) - 1:
                        output += "|"
                output += "\n"
                file.write(output)
        elif option == "json":
            columns = column_names[filename]

            file.write("[\n")

            for i in range(len(value)):
                row = value[i]
                output = {}
                for j in range(len(row)):
                    output[columns[j]] = str(row[j])
                json.dump([output], file)

                if i != len(value) - 1:
                    file.write(",\n")

            file.write("\n]")


def export_db(option):
    table_list = ["Category", "Activities", "MandatoryActivity", "MandatoryGoal", "MandatoryGoalAux",
                  "MandatoryEntries", "DailyGoal", "DailyGoalAux", "Entries"]

    pb = lchalk.progress_bar(len(table_list))
    pb.start()

    con = sqlite3.connect(path_to_database)
    cur = con.cursor()

    for i in range(len(table_list)):
        query = f"SELECT * FROM {table_list[i]}"
        cur.execute(query)
        value = cur.fetchall()

        filename = table_list[i]

        write_to_export_file(option, value, filename)
        pb.step()

    con.close()
    return True


def mand_act_ids_valid(id_set):
    con = sqlite3.connect(path_to_database)
    cur = con.cursor()
    for number in id_set:
        cur.execute("SELECT * FROM MandatoryActivity WHERE MandatoryActivityID = ?", (number,))
        value = cur.fetchall()
        if not value:
            return False
    return True


def add_mand_obj():
    try:
        con = sqlite3.connect(path_to_database)
        cur = con.cursor()
        cur.execute('SELECT * FROM MandatoryActivity')
        value = cur.fetchall()
        if not value:
            raise SQLError("la table ’MandatoryActivity’ est vide !")

        for row in value:
            print("\t{:<3} {:<5} {:<50}".format(lchalk.colorize(str(row[0]), "yellow"),
                                                 " ", row[1]))

        x = input(lchalk.colorize("\nEntre les nombres pour les activités obligatoires, séparés par le ',' :\n",
                                      "yellow"))

        mand_act_ids = set()
        for number in x.split(','):
            mand_act_ids.add(int(number))

        if not mand_act_ids_valid(mand_act_ids):
            raise SQLError("quelque(s) ID(s) n'est (ne sont) pas bon.")

        cur.execute("SELECT MandatoryGoalID FROM MandatoryGoal ORDER BY MandatoryGoalID DESC LIMIT 1")
        value = cur.fetchall()
        mand_goal_id = 1
        if not value:
            value = 1
        else:
            value = value[0][0] + 1
            mand_goal_id = value

        cur.execute("INSERT INTO MandatoryGoal VALUES(?, ?)", (value,
                                                               get_lazarus_day().strftime("%Y-%m-%d")))
        con.commit()

        cur.execute("SELECT MandatoryGoalAuxID FROM MandatoryGoalAux ORDER BY MandatoryGoalAuxID DESC LIMIT 1")
        mand_aux_id = 1
        value = cur.fetchall()
        if value:
            mand_aux_id = value[0][0] + 1

        for number in mand_act_ids:
            cur.execute("INSERT INTO MandatoryGoalAux VALUES(?, ?, ?)", (mand_aux_id, mand_goal_id, number))
            con.commit()
            mand_aux_id += 1

        con.close()
        return True

    except SQLError as e:
        lchalk.colorize_and_print(str(e) + "\n", "yellow")
        return False
    except Exception as e:
        lchalk.colorize_and_print("Error: " + str(e) + "\n", "yellow")
        return False


# 0 -> activity
# 1 -> category
# -1 -> neither
def check_act_or_cat(name):
    con = sqlite3.connect(path_to_database)
    cur = con.cursor()
    cur.execute("SELECT * FROM Activities WHERE LOWER(Name) = ?", (name.lower(),))
    value = cur.fetchall()
    if value:
        return 0

    cur.execute("SELECT * FROM Category WHERE LOWER(Name) = ?", (name.lower(),))
    value = cur.fetchall()
    if value:
        return 1

    return -1


def add_obj():
    try:
        list_everything()

        lchalk.colorize_and_print("\nFormat : [nom de l'activité], [temps cible]. Tape 'exit' pour finir.",
                        "yellow")

        target_acts = []
        while True:
            try:
                x = input()

                if x == "exit":
                    break

                isCat = check_act_or_cat(x.split(',')[0])
                if isCat < 0 or int(x.split(',')[1]) <= 0 or int(x.split(',')[1]) > 1440:
                    raise Exception("Entré incorrect.")

                temp = []
                temp.append(x.split(',')[0])
                temp.append(int(x.split(',')[1]))
                target_acts.append(temp)

            except Exception as e:
                print(str(e))

        con = sqlite3.connect(path_to_database)
        cur = con.cursor()
        cur.execute("SELECT DailyGoalID FROM DailyGoal ORDER BY DailyGoalID DESC LIMIT 1")
        value = cur.fetchall()
        daily_goal_id = 1
        if value:
           daily_goal_id = value[0][0] + 1

        cur.execute("INSERT INTO DailyGoal VALUES(?, ?)", (daily_goal_id,
                                                           get_lazarus_day().strftime("%Y-%m-%d")))
        con.commit()

        cur.execute("SELECT DailyGoalAuxID FROM DailyGoalAux ORDER BY DailyGoalAuxID DESC LIMIT 1")
        daily_aux_id = 1
        value = cur.fetchall()
        if value:
            daily_aux_id = value[0][0] + 1

        for pair in target_acts:
            act_cat_id = 0
            isCat = check_act_or_cat(pair[0])
            if isCat == 0:
                act_cat_id = get_activity_id(pair[0])
            else:
                act_cat_id = get_category_id(pair[0])
            
            cur.execute("INSERT INTO DailyGoalAux VALUES(?, ?, ?, ?, ?)", (daily_aux_id, daily_goal_id,
                                                                           act_cat_id, pair[1], isCat))
            con.commit()
            daily_aux_id += 1

        con.close()
        return True

    except SQLError as e:
        lchalk.colorize_and_print(str(e) + "\n", "yellow")
        return False
    except Exception as e:
        lchalk.colorize_and_print("Error: " + str(e) + "\n", "yellow")
        return False


def first_date():
    con = sqlite3.connect(path_to_database)
    cur = con.cursor()
    cur.execute("SELECT WorkDate FROM Entries ORDER BY WorkDate ASC LIMIT 1")
    return datetime.strptime(str(cur.fetchall()[0][0]), "%Y-%m-%d")


def get_category_name(activity):
    con = sqlite3.connect(path_to_database)
    cur = con.cursor()
    cur.execute("SELECT Category.Name FROM Category JOIN Activities ON Category.SubCategoryID = Activities.SubCategoryID WHERE Activities.Name = ?", (activity,))
    return cur.fetchall()[0][0]

def print_stats(flags, category_name):
    try:
        # c -> specify category
        # t -> top 10
        # w -> past week
        # m -> past month
        # y -> past year
        # a -> all time
        possible_flags = ['c', 't', 'w', 'm', 'y', 'a']
        if flags is not None and flags[1:] == "":
            flags = None
        if flags is not None:
            flags = flags[1:]

        if flags is None:
            print("{:<20} {:<20} {:<25} {:<27} {:<25} {:<20}".format("", lchalk.colorize("%BS", "yellow"),
                                                                     lchalk.colorize("% de chang.", "yellow"),
                                                                     lchalk.colorize("H. travaillé", "yellow"),
                                                                     lchalk.colorize("Heures totales", "yellow"),
                                                                     lchalk.colorize("%BS moyen", "yellow")))

            pbs_arr = []
            pbs_change = []
            hrs_worked = []

            tail = get_lazarus_day()

            # if tail is Sunday, go to last Sunday
            if tail.weekday() == 6:
                tail = tail - timedelta(1)

            while tail.weekday() != 6:
                tail = tail - timedelta(1)

            con = sqlite3.connect(path_to_database)
            cur = con.cursor()

            head = tail - timedelta(6)

            for i in range(5):
                head_str = head.strftime("%Y-%m-%d")
                tail_str = tail.strftime("%Y-%m-%d")

                cur.execute("SELECT SUM(WorkTime) FROM Entries WHERE WorkDate >= ? AND WorkDate <= ?",
                            (head_str, tail_str))
                value = cur.fetchall()
                if not value[0][0]:
                    hrs_worked.append(0)
                else:
                    hrs_worked.append(value[0][0] / 60.0)

                # go back a week
                tail = head - timedelta(1)
                head = head - timedelta(7)

            # get those sweet 8 hours of sleep, man
            hrs_awake = 24 * 7 - 8 * 7

            # index 0 is last week; index 4 is 5 weeks ago
            for i in range(5):
                res = (hrs_worked[i] / hrs_awake) * 100
                pbs_arr.append(res)

            total_hrs_worked = 0
            pbs_avg = (pbs_arr[0] + pbs_arr[1] + pbs_arr[2] + pbs_arr[3]) / 4
            for i in range(4):
                if pbs_arr[i + 1] != 0:
                    percent_change = -((pbs_arr[i + 1] - pbs_arr[i]) / pbs_arr[i + 1]) * 100
                    pbs_change.append(percent_change)
                else:
                    pbs_change.append("+∞")
                total_hrs_worked += hrs_worked[i]

            for i in range(4):
                time_period = ""
                pbs_change_string = ""
                if pbs_change[i] == "+∞":
                    pbs_change_string = lchalk.colorize("+∞", "green")
                else:
                    pbs_change_string = "{:+.1f}%".format(pbs_change[i])
                    if pbs_change[i] < 0:
                        pbs_change_string = lchalk.colorize(pbs_change_string, "red")
                    elif pbs_change[i] > 0:
                        pbs_change_string = lchalk.colorize(pbs_change_string, "green")
                    elif pbs_change[i] == 0:
                        pbs_change_string = lchalk.colorize(pbs_change_string, "yellow")

                if i == 0:
                    time_period = "Il y a " + str(i + 1) + " semaine "
                else:
                    time_period = "Il y a " + str(i + 1) + " semaines"

                if i == 0:
                    print("{:<20} {:<13.1f} {:<16} {:10} {:<10.1f} {:>13.1f} {:>13.1f}".format(time_period,
                                                                                               pbs_arr[i],
                                                                                               pbs_change_string, "",
                                                                                               hrs_worked[i],
                                                                                               total_hrs_worked,
                                                                                               pbs_avg))
                else:
                    print("{:<20} {:<13.1f} {:<16} {:10} {:<10.1f}".format(time_period, pbs_arr[i],
                                                                           pbs_change_string, "", hrs_worked[i]))

            con.close()
            print()
        else:
            for char in flags:
                if char not in possible_flags:
                    raise Exception("quelque drapeau n'est pas valide.")

            if 'c' in flags and category_name == "":
                raise Exception("catégorie non précisée.")
            if 'c' in flags and get_category_id(category_name) is None:
                raise Exception("catégorie n'est pas valide.")

            end_date = get_lazarus_day().strftime("%Y-%m-%d")
            start_date = get_lazarus_day()

            time_flag_set = False

            if 'w' in flags:
                while start_date.weekday() != 0:
                    start_date = start_date - timedelta(1)
                time_flag_set = True
            if 'm' in flags:
                if time_flag_set:
                    raise Exception("quelque drapeau n'est pas valide.")
                while start_date.day != 1:
                    start_date = start_date - timedelta(1)
                time_flag_set = True
            if 'y' in flags:
                if time_flag_set:
                    raise Exception("quelque drapeau n'est pas valide.")
                start_date = start_date.strptime(str(start_date.year) + "-01-01", "%Y-%m-%d")
                time_flag_set = True
            if 'a' in flags or not time_flag_set:
                if time_flag_set:
                    raise Exception("quelque drapeau n'est pas valide.")
                start_date = first_date()

            start_date_obj = start_date
            start_date = start_date.strftime("%Y-%m-%d")

            sql = "SELECT SUM(Entries.WorkTime) AS 'Time', Activities.Name FROM Entries JOIN Activities ON Entries.ActivityID = Activities.ActivityID WHERE WorkDate >= ? AND WorkDate <= ?"
            if 'c' in flags:
                sql += " AND Activities.SubCategoryID = ?"
            sql += " GROUP BY Activities.Name ORDER BY Time DESC"
            if 't' in flags:
                sql += " LIMIT 10"

            con = sqlite3.connect(path_to_database)
            cur = con.cursor()
            if 'c' in flags:
                cur.execute(sql, (start_date, end_date, get_category_id(category_name)))
            else:
                cur.execute(sql, (start_date, end_date))

            value = cur.fetchall()
            print("{:>15} {}".format("(Période : ", "de " + lchalk.colorize(format_date(start_date_obj), "yellow") + " à " + lchalk.colorize(format_date(get_lazarus_day()), "yellow") + ")\n"))
            print("{:>15} {:2} {:<39} {:<15} {:>20}".format(lchalk.colorize("#", "yellow"),
                                                           "", lchalk.colorize("Nom de l'activité", "yellow"),
                                                           lchalk.colorize("Temps", "yellow"),
                                                           lchalk.colorize("Catégorie", "yellow")))

            cnt = 1
            total = 0
            for row in value:
                cat_name = get_category_name(row[1])
                cat_id = (get_category_id(cat_name) - 1) % 6
                total += float(row[0])
                color = "white"
                if cat_id == 1:
                    color = "blue"
                elif cat_id == 2:
                    color = "green"
                elif cat_id == 3:
                    color = "cyan"
                elif cat_id == 4:
                    color = "red"
                elif cat_id == 5:
                    color = "magenta"
                elif cat_id == 6:
                    color = "yellow"
                print("{:>6} {:2} {:<20} {:>15} {:2} {:<20}".format(cnt, "", row[1],
                                                                    "{:.1f}".format(float(row[0])/60),
                                                                    "",
                                                                    lchalk.colorize(cat_name, color)))
                cnt += 1
            print("\n{:>36} {:>9.1f}\n".format("Σ:", total/60))

    except Exception as e:
        lchalk.colorize_and_print("Error: " + str(e) + "\n", "yellow")


def calculate_trend():
    today = datetime.today().now()
    days_since_monday = today.weekday()  # Monday is 0, Sunday is 6
    if days_since_monday == 0 and today.hour < 5:
        days_since_monday = 7
    hrs_since_5AM_MON = (days_since_monday * 24 + today.hour + today.minute / 60) - 5
    hrs_awake = days_since_monday * 16

    if hrs_since_5AM_MON % 24 <= 16:
        hrs_awake += hrs_since_5AM_MON % 24
    elif hrs_since_5AM_MON % 24 > 16:
        hrs_awake += 16


    total_hrs_awake_in_week = 7*16
    hrs_left = total_hrs_awake_in_week - hrs_awake
    work_per_hr = 0
    if hrs_awake != 0:
        work_per_hr = get_this_week_worked()/(hrs_awake*60.)

    projected_worktime = get_this_week_worked()/60. + hrs_left*work_per_hr
    print("Temps projeté jusqu'à la fin de la semaine : " + lchalk.colorize("{:.1f}".format(projected_worktime), "yellow") + " h.\n")


if __name__ == "__main__":
    try:
        notification = ""
        delim = ""
        title_color = lchalk.randomize_color()
        while title_color == "black":
            title_color = lchalk.randomize_color()
        refresh()
        while True:
            x = ""

            try:
                # To 'activate' a new notification, just change to something other
                # than an empty string.
                if notification != "":
                    print(notification, end='', flush=True)
                    time.sleep(1)
                    notification = ""
                    refresh()
                    continue

                # clears the line so that the user can't delete the '$' char
                sys.stdout.write("\033[K")
                x = input("$ ")

            except KeyboardInterrupt:
                print()
                sys.stdout.flush()
                sys.exit(0)

            matches = [re.fullmatch(r"^help *$", x),  # 0
                       re.fullmatch(r"^exit *$", x),  # 1
                       re.fullmatch(r"^backup *$", x),  # 2
                       re.fullmatch(r"^clear *$", x),  # 3
                       re.fullmatch(r"^motivation *$", x),  # 4
                       re.fullmatch(r"^list *$", x),  # 5
                       re.fullmatch(r"^add act '([a-zA-Z0-9 ]*)' '([a-zA-Z0-9 ]*)' '([a-zA-Z0-9 ]*)' *$", x),  # 6
                       re.fullmatch(r"^add mand act '([a-zA-Z0-9 ]*)' *$", x),  # 7
                       re.fullmatch(r"^c ([a-zA-Z0-9 ]*)$", x),  # 8
                       re.fullmatch(r"^add obj *$", x),  # 9
                       re.fullmatch(r"^add mand obj *$", x),  # 10
                       re.fullmatch(r"^export (json|psv) *$", x),  # 11
                       re.fullmatch(r"^stats *(-[a-z]*)? *([a-zA-Z]*)?$", x),  # 12
                       re.fullmatch(r"^(hier *|(?:(\d*)h)?(?:(\d*)(?:min|'))?) *$", x.split(' ')[0]), # 13
                       re.fullmatch(r"^trend *$", x)]  # 14
            if matches[0]:
                print()
                for i in range(len(commands)):
                    print("\t{:<15} {:<50} {:<100}".format(commands[i][0], commands[i][1], commands[i][2]), end="")
                print()

            elif matches[1]:
                print()
                sys.exit(0)

            elif matches[2]:
                desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
                source_file = path_to_database
                destination_file = os.path.join(desktop_path, "db_backup" + str(int(time.time())))
                shutil.copy(source_file, destination_file)
                notification = lchalk.colorize("Sauvegardé avec succès.", "green")

            elif matches[3]:
                refresh()

            elif matches[4]:
                quotes = [
                    "A man is the sum of his actions, of what he has done, of what he can do. Nothing else.\n-John Galsworthy",
                    "One must imagine Sisyphus happy.\n-Albert Camus",
                    "Nothing in my life has ever happened for me on the first try.\n-David Goggins",
                    "And remember, your greatness is not tied to any outcome.\nIt is found in the valiance of the attempt.\n-David Goggins",
                    "Setting an example through action rather than words will always\nbe the most potent form of leadership, and it’s available to all of us.\n-David Goggins",
                    "I’m afraid a lot, but I’ve learned to flip fear by facing whatever it is I’m scared of head-on.\n-David Goggins",
                    "We are all in the gutter, but some of us are looking at the stars.\n-Oscar Wilde",
                    "Everything you can imagine is real.\n-Pablo Picasso",
                    "No matter how troubled or hopeless or sheltered your environment is,\nit is your job, your obligation, your duty, and your responsibility to yourself\nto find the blue-to-black line—that glimmer—buried in your soul and seek greatness.\nNobody can show you that glimmer. You must do the work to discover it on your own.\n-David Goggins"]

                rand_numb = random.randint(0, len(quotes) - 1)
                print(quotes[rand_numb] + "\n")

            elif matches[5]:
                list_everything()

            elif matches[6]:
                if insert_activity(matches[6].group(1), matches[6].group(2), matches[6].group(3)):
                    notification = lchalk.colorize("Entré avec succès.", "green")

            elif matches[7]:
                if insert_mand_activity(matches[7].group(1)):
                    notification = lchalk.colorize("Entré avec succès.", "green")

            elif matches[8]:
                if complete_mand_act(matches[8].group(1)):
                    notification = lchalk.colorize("Activité complété.", "green")

            elif matches[9]:
                if add_obj():
                    notification = lchalk.colorize("Enregistré avec succès.\n", "green")

            elif matches[10]:
                if add_mand_obj():
                    notification = lchalk.colorize("Enregistré avec succès.\n", "green")

            elif matches[11]:
                if export_db(matches[11].group(1)):
                    lchalk.colorize_and_print("Exportation fini avec succès.\n", "green")

            elif matches[12]:
                print_stats(matches[12].group(1), matches[12].group(2))

            elif matches[13]:
                work_input = re.fullmatch(r"^(hier *)?(?:(\d*)h)?(?:(\d*)(?:min|'))? *([a-zA-Z0-9 ]*)$", x)

                isYesterday = False

                total_time = 0

                hours = work_input.group(2)
                minutes = work_input.group(3)
                activity_name = work_input.group(4)

                if work_input.group(1) is not None:
                    isYesterday = True
                if hours is not None:
                    total_time += int(hours)*60
                if minutes is not None:
                    total_time += int(minutes)

                if activity_name is not None:
                    if insert_new_entry(total_time, activity_name, isYesterday):
                        notification = lchalk.colorize("Entré avec succès.", "green")
                else:
                    lchalk.colorize_and_print("Entre le nom de l'activité.\n", "yellow")

            elif matches[14]:
                calculate_trend()

            else:
                lchalk.colorize_and_print("Commande inconnue.\n", "yellow")

    except KeyboardInterrupt:
        print()
        sys.stdout.flush()
        sys.exit(0)
    except Exception as e:
        print(e)

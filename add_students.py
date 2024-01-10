import bcrypt
import csv
import json
import random
import mariadb
import sys

from domjudge_team import DomjudgeTeam
from domjudge_user import DomjudgeUser
from student import Student
from user import User

# Whether to assign a new password to already existing users.
assign_new_password_to_existing_users = False

def load_json_file(file_path):
	with open(file_path, "r") as f:
		return json.load(f)

def load_db_config(file_path):
	return load_json_file(file_path)

def load_exam_config(file_path):
	return load_json_file(file_path)

def load_students(file_path):
	students = []

	with open(file_path, "r") as f:
		reader = csv.DictReader(f)

		for row in reader:
			student = Student(
				row["Codice persona"],
				row["Matricola"],
				row["Cognome-Nome"],
				row["E-mail"])

			students.append(student)

	return students

def get_db_connection(db_config):
	return mariadb.connect(
		host = db_config["host"],
		port = db_config["port"],
		user = db_config["user"],
		password = db_config["password"],
		database = db_config["database"])

def compose_domjudge_username(student):
	return student.person_code + "-esami"

def gen_random_password(n):
	# Define the list of choices of characters.
	characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

	# Generate the password.
	return "".join(random.sample(characters, n))

def hash_password(password):
	bytes = password.encode('utf-8')
	salt = bcrypt.gensalt()
	return bcrypt.hashpw(bytes, salt)

def domjudge_get_role_id(db, role):
	cursor = db.cursor()
	cursor.execute("SELECT roleid FROM role WHERE role=?", (role,))
	roles = list(cursor)
	cursor.close()

	if len(roles) == 0:
		raise Exception("Role " + role + " not found")
	elif len(roles) == 1:
		return roles[0][0]
	else:
		raise Exception("Multiple roles named " + role)

def domjudge_get_team_category_id(db, name):
	cursor = db.cursor()
	cursor.execute("SELECT categoryid FROM team_category WHERE name=?", (name,))
	roles = list(cursor)
	cursor.close()

	if len(roles) == 0:
		raise Exception("Team category " + role + " not found")
	elif len(roles) == 1:
		return roles[0][0]
	else:
		raise Exception("Multiple team categories named " + role)

def domjudge_get_contest_id(db, shortname):
	cursor = db.cursor()
	cursor.execute("SELECT cid FROM contest WHERE shortname=?", (shortname,))
	cursor_contests = list(cursor)
	cursor.close()

	if len(cursor_contests) == 0:
		raise Exception("Contest " + contest_name + " not found")
	elif len(cursor_contests) == 1:
		return cursor_contests[0][0]
	else:
		raise Exception("Multiple contests named " + contest_name)

def domjudge_get_user(db, username):
	cursor = db.cursor()

	cursor.execute(
		"SELECT userid, username, teamid FROM user WHERE username = %s",
		(username,))

	users = list(cursor)
	cursor.close()

	if len(users) > 1:
		raise Exception("Multiple users named " + username)
	elif len(users) == 0:
		return None

	return DomjudgeUser(users[0][0], users[0][1], users[0][2])

def domjudge_create_user(db, username, password, name, email):
	hashed_password = hash_password(password)
	cursor = db.cursor()

	cursor.execute(
		"INSERT INTO user(username, name, email, password) VALUES(?,?,?,?)",
		(username, name, email, hashed_password))

	user = DomjudgeUser(cursor.lastrowid, username, None)
	print("Created user for", username, "with ID", user.id)
	return user

def domjudge_set_user_password(db, user_id, password):
	hashed_password = hash_password(password)
	cursor = db.cursor()

	cursor.execute(
		"UPDATE user SET password=? WHERE userid=?",
		(hashed_password, user_id))

	print("Updated password of user", user_id, "to", password)

def domjudge_add_role_to_user(db, user_id, role_id):
	cursor = db.cursor()

	cursor.execute(
		"SELECT COUNT(*) FROM userrole WHERE userid=? AND roleid=?",
		(user_id, role_id))

	if cursor.fetchone()[0] == 0:
		cursor.execute(
			"INSERT INTO userrole(userid, roleid) VALUES(?, ?)",
			(user_id, role_id))

		print("Added role", role_id, "to user", user_id)

def domjudge_get_team(db, name):
	cursor = db.cursor()

	cursor.execute(
		"SELECT teamid, name, display_name FROM team WHERE name=?",
		(name,))

	teams = list(cursor)

	if len(teams) > 1:
		raise Exception("Multiple teams named " + name)
	elif len(teams) == 0:
		return None

	return DomjudgeTeam(teams[0][0], teams[0][1], teams[0][2])

def domjudge_create_team(db, name, display_name, team_category_id):
	cursor = db.cursor()

	cursor.execute(
		"INSERT INTO team(name, display_name, categoryid) VALUES(?,?,?)",
		(name, display_name, team_category_id))

	team = DomjudgeTeam(cursor.lastrowid, name, display_name)
	print("Created team for", name, "with ID", team.id)
	return team

def domjudge_assign_user_to_team(db, user_id, team_id):
	cursor = db.cursor()

	cursor.execute(
		"UPDATE user SET teamid=? WHERE userid=?",
		(team_id, user_id))

	print("User with", user_id, "assigned to team with ID", team_id)

def domjudge_add_team_to_contest(db, team_id, contest_id):
	cursor = db.cursor()

	cursor.execute(
		"SELECT COUNT(*) FROM contestteam WHERE cid=? AND teamid=?",
		(contest_id, team_id))

	if cursor.fetchone()[0] == 0:
		cursor.execute(
			"INSERT INTO contestteam(cid, teamid) VALUES(?, ?)",
			(contest_id, team_id))

		print("Added team", team_id, "to contest", contest_id)

def run(db_config, exam_config, students):
	users = []
	failed_student_person_codes = []

	# Get the connection to the database.
	try:
		db = get_db_connection(db_config)
	except Exception as ex:
		print(ex)
		raise Exception("Can't connect to the database")

	# Get the contest ID.
	contest_id = domjudge_get_contest_id(db, exam_config["shortname"])

	# Get the 'team' role ID.
	role_id = domjudge_get_role_id(db, "team")
	
	# Get the team category ID.
	team_category_id = domjudge_get_team_category_id(db, exam_config["team_category"])

	for student in students:
		try:
			print("----------------------------------------------")

			domjudge_username = compose_domjudge_username(student)
			password = gen_random_password(12)

			# Get the Domjudge user, if already existing.
			domjudge_user = domjudge_get_user(db, domjudge_username)

			if domjudge_user == None:
				# User doesn't exist.
				domjudge_user = domjudge_create_user(
					db, domjudge_username, password, student.name, student.email)

				domjudge_add_role_to_user(db, domjudge_user.id, role_id)
			else:
				# User already exists.
				print("Student", student.person_code, "alread exists with ID", domjudge_user.id)

				if assign_new_password_to_existing_users == True:
					# Set the new password.
					domjudge_set_user_password(db, domjudge_user.id, password)

			# Get the Domjudge team, if already existing.
			domjudge_team = domjudge_get_team(db, domjudge_username)

			if domjudge_team == None:
				# Team doesn't exist.
				domjudge_team = domjudge_create_team(
					db, domjudge_username, student.person_code, team_category_id)
			else:
				# Team already exists.
				print("Team", domjudge_team.name, "already exists with ID", domjudge_team.id)

			# Assign the user to the team.
			domjudge_assign_user_to_team(db, domjudge_user.id, domjudge_team.id)

			# Add the team to the contest.
			domjudge_add_team_to_contest(db, domjudge_team.id, contest_id)

			# Confirm the modifications to the database.
			db.commit()

			# Store the information about the user.
			users.append(User(student.name, domjudge_username, password))

			print("----------------------------------------------\n")
		except Exception as ex:
			print("Error while processing user " + student.person_code + ":\n", ex)

			# Cancel the modifications made to the database for the current student.
			db.rollback()

			# Keep track of the students that have not been added to the database
			failed_student_person_codes.append(student.person_code)

	# Close the connection to the database.
	db.close()

	# Write the credentials to file.
	with open("credentials.txt", "w") as credentials_file:
		for user in users:
			credentials_file.write("--------------------------------\n")
			credentials_file.write(user.name)
			credentials_file.write("\n")
			credentials_file.write("USERNAME: ")
			credentials_file.write(user.username)
			credentials_file.write("\n")
			credentials_file.write("PASSWORD: ")
			credentials_file.write(user.password)
			credentials_file.write("\n")
			credentials_file.write("--------------------------------\n\n")

	# Print the users for which the insertion failed.
	print("Students for which the insertion failed:", failed_student_person_codes)

if __name__ == '__main__':
	# Check for command line arguments correctness.
	if len(sys.argv) != 4:
		print("Usage:", sys.argv[0], "db-config.json exam-config.json students.csv")
		exit(-1)

	db_config_file = sys.argv[1]
	exam_config_file = sys.argv[2]
	students_file = sys.argv[3]

	# Load the database connection parameters.
	try:
		db_config = load_db_config(db_config_file)
	except Exception as ex:
		print("Can't open file", db_config_file, "due to the following error:\n", ex)
		exit(-1)

	# Load the exam configuration parameters.
	try:
		exam_config = load_exam_config(exam_config_file)
	except Exception as ex:
		print("Can't open file", exam_config_file, "due to the following error:\n", ex)
		exit(-1)

	# Load the students registered to the exam.
	try:
		students = load_students(students_file)
	except Exception as ex:
		print("Can't open file", students_file, "due to the following error:\n", ex)
		exit(-1)

	# Run the main program.
	run(db_config, exam_config, students)

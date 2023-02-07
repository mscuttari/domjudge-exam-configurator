import bcrypt
import csv
import json
import random
import mariadb
import os
import sys

from domjudge_team import DomjudgeTeam
from domjudge_user import DomjudgeUser
from student import Student
from submission import Submission
from test_case import TestCase
from user import User

submissions_path = "submissions"

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
	return "polimi-" + student.person_code

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

def domjudge_get_problem_id(db, problem_name):
	cursor = db.cursor()
	cursor.execute("SELECT probid FROM problem WHERE name = ?", (problem_name,))
	cursor_problems = list(cursor)
	cursor.close()

	if len(cursor_problems) == 0:
		raise Exception("Problem " + problem_name + " not found")
	elif len(cursor_problems) == 1:
		return cursor_problems[0][0]
	else:
		raise Exception("Multiple problems named " + problem_name)

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

def domjudge_get_user_submissions_for_problem(db, user_id, contest_id, problem_id):
	submissions = []
	cursor = db.cursor()

	cursor.execute(
		"SELECT s.submitid, s.submittime, sf.sourcecode, j.result " \
		"FROM submission AS s JOIN submission_file AS sf ON s.submitid = sf.submitid JOIN judging AS j ON s.submitid = j.submitid " \
		"WHERE s.userid = ? AND s.cid = ? AND s.probid = ? AND s.valid = ? AND j.valid = ? " \
		"ORDER BY s.submittime DESC",
		(user_id, contest_id, problem_id, 1, 1))

	for submission in cursor:
		submissions.append(Submission(
			submission[0], submission[1], submission[2], submission[3]))

	cursor.close()
	return submissions

def domjudge_get_submission_test_cases(db, submission_id):
	test_cases = []
	cursor = db.cursor()

	cursor.execute(
		"SELECT t.testcaseid, t.ranknumber, t.description, jr.runresult " \
		"FROM submission AS s JOIN judging AS j ON s.submitid = j.submitid JOIN judging_run AS jr ON j.judgingid = jr.judgingid JOIN testcase as t ON jr.testcaseid = t.testcaseid " \
		"WHERE s.submitid = ? AND s.valid = ? AND j.valid = ? " \
		"ORDER BY t.ranknumber ASC",
		(submission_id,1,1))

	for test_case in cursor:
		test_cases.append(TestCase(
			test_case[0], test_case[1], test_case[2], test_case[3]))

	cursor.close()
	return test_cases

def run(db_config, exam_config, students):
	failed_student_person_codes = []

	# Get the connection to the database.
	try:
		db = get_db_connection(db_config)
	except Exception as ex:
		print(ex)
		raise Exception("Can't connect to the database")

	# Get the contest ID.
	contest_id = domjudge_get_contest_id(db, exam_config["shortname"])

	# Get the names of the problems of the exam.
	problem_names = exam_config["problem_names"]

	# Iterate over all the students that are registered to the exam.
	for student in students:
		try:
			print("----------------------------------------------")
			print("Processing student", student.person_code)

			domjudge_username = compose_domjudge_username(student)
			domjudge_user = domjudge_get_user(db, domjudge_username)

			if domjudge_user == None:
				raise Exception("User not found")

			# Create the folder for the student.
			student_path = submissions_path + "/" + student.person_code

			if not os.path.exists(student_path):
				os.makedirs(student_path)

			for problem_name in problem_names:
				problem_path = student_path + "/" + problem_name
				problem_id = domjudge_get_problem_id(db, problem_name)
				submissions = domjudge_get_user_submissions_for_problem(
					db, domjudge_user.id, contest_id, problem_id)

				number_of_submissions = len(submissions)
				print("\nFound", number_of_submissions, "submissions for problem", problem_name)

				if number_of_submissions > 0:
					# Create the folder for the current problem.
					if not os.path.exists(problem_path):
						os.makedirs(problem_path)

					# Determine the submission to be used as proposed solution.
					# It is determined by the last correct solution, if any, or by the
					# last sent code in case of no correct answers.
					final_submission = submissions[0]

					for s in submissions:
						if s.result == "correct":
							final_submission = s
							break

					# Compute the statistics about this submission.
					test_cases = domjudge_get_submission_test_cases(db, final_submission.id)

					print("Final submission:")
					print(" - Time " + str(final_submission.time))
					print(" - Result: " + final_submission.result)

					# Write the final submission to file.
					source_file_path = problem_path + "/main.c"
					print("Writing source code to \"" + source_file_path + "\"")

					with open(source_file_path, "wb") as source_file:
						source_file.write(final_submission.source_code)

					# Write the statistics about this submission.
					test_cases_file_path = problem_path + "/test_cases.txt"
					print("Writing the test cases information to \"" + test_cases_file_path + "\"")

					with open(test_cases_file_path, "w") as test_cases_file:
						test_cases_file.write("Overall result: " + final_submission.result + "\n")
						correct = 0

						for test_case in test_cases:
							if test_case.result == "correct":
								correct += 1

						test_cases_file.write("Passed " + str(correct) + " tests cases out of " + str(len(test_cases)) + "\n\n")

						for test_case in test_cases:
							test_cases_file.write("# Test case " + str(test_case.number) + "\n")
							test_cases_file.write(" - Description: \"" + test_case.description.decode("UTF-8") + "\"\n")
							test_case_result_str = "not evaluated"

							if test_case.result != None:
								test_case_result_str = test_case.result

							test_cases_file.write(" - Result: " + test_case_result_str  + "\n\n")

			# Confirm the modifications to the database.
			db.commit()

			print("----------------------------------------------\n")
		except Exception as ex:
			print("Error while processing student " + student.person_code + ":\n", ex)

			# Cancel the modifications made to the database for the current student.
			db.rollback()

			# Keep track of the students that have not been added to the database
			failed_student_person_codes.append(student.person_code)

	# Close the connection to the database.
	db.close()

	# Print the users for which the insertion failed.
	print("Students for which the download failed:", failed_student_person_codes)

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

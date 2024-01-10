# DOMJudge exam configurator
## Dependencies
Install the required OS dependencies.
The procedure varies according to the package manager in use.
```
libmariadb-dev
```

Create a Python virtual environment and activate it:
```shell
python3 -m venv .venv
source .venv/bin/activate
```

Install the required Python dependencies:
```shell
python3 -m pip install -r requirements.txt
```

## Usage
To add the students to an exam:
```shell
python add_students.py db-config-file exam-config-file students.csv
```
To download the solutions submitted by students for an exam:
```shell
python download_exams.py db-config-file exam-config-file students.csv
```

## File formats

- `db-config-file`: path of the JSON file containing the parameters to be used for the connection to the database
  - `user`: name of the user with write access to the DOMJudge database
  - `password`: password of the above user
  - `host`: where the database is hosted
  - `port`: connection port
  - `database`: name of the DOMJudge database
```json
{
  "user": "domjudge",
  "password": "password",
  "host": "localhost",
  "port": 3306,
  "database": "domjudge"
}
```

- `exam-config-file`: path of the JSON file containing the information about the exam
  - `shortname`: the shortname that has been specified while creating the contest through the DOMJudge web interface
```json
{
  "shortname": "exam",
  "problem_shortnames": ["Shortname 1", "Shortname 2"],
  "team_category"; "Team category name"
}
```

   - `students.csv`: path of the CSV file containing the students registered to the exam

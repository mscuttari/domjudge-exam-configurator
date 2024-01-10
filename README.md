# DOMJudge exam configurator
## Usage
To add the students to an exam:
```shell
python add_students.py db-config-file exam-config-file students.csv
```
To download the solutions submitted by students:
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
  "shortname": "exam"
}
```

   - `students.csv`: path of the CSV file containing the students registered to the exam

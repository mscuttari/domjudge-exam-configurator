class Student:
	def __init__(self, person_code, id_number, name, email):
		self.person_code = person_code
		self.id_number = id_number
		self.name = name
		self.email = email

	def __repr__(self):
		return "{person_code: %s, id_number: %s, name: %s, email: %s" % \
			(self.person_code, self.id_number, self.name, self.email)

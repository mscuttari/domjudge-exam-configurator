class User:
	def __init__(self, name, username, password):
		self.name = name
		self.username = username
		self.password = password

	def __repr__(self):
		return "{name: %s, username: %s, password: %s}" % \
			(self.name, self.username, self.password)

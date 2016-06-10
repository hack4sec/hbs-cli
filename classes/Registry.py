class Registry:
	data = {}
	def get(self, key):
		return Registry.data[key]
	def set(self, key, value):
		Registry.data[key] = value
	def isset(self, key):
		return key in Registry.data
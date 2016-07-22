from classes.Database import Database
from classes.Registry import Registry


class Factory:
    def new_db_connect(self):
        """ Function return new mysql connection (for multiple usage in threads) """
        config = Registry().get('config')
        return Database(
            config['main']['mysql_host'],
            config['main']['mysql_user'],
            config['main']['mysql_pass'],
            config['main']['mysql_dbname']
        )
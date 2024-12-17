import sys

class Command:
    def execute(self):
        pass

    @staticmethod
    def getCommandTable(table, helpCommand, obj):
        if table == 'known':
            return obj.knownTable
        elif table == 'unknown':
            return obj.unknownTable
        else:
            print(helpCommand())
            print(f'Invalid table: {table}')
            return 0

class HelpCommand(Command):
    @staticmethod
    def execute():
        print("""
Usage: python script.py [COMMAND] [OPTIONS]

Commands:
    {0}
    {1}
    {2}
    {3}
    {4}

Examples:
    python script.py -s known       # Display entries from the 'known' table.
    python script.py -u unknown     # Update the 'unknown' table based on ARP scan.
    python script.py -i known 'Device1' '00:1A:2B:3C:4D:5E'  # Insert a known entry with name and MAC.
    python script.py -d unknown ip '192.168.1.100'  # Delete an unknown entry based on IP address.
    python script.py -uc known mac '00:1A:2B:3C:4D:5E' ip '192.168.1.101' # Updates the 'ip' column in the 'known' table where 'mac' matches '00:1A:2B:3C:4D:5E'.

Notes:
    - The ARP scan is used to update the IP addresses for known MAC addresses.
    - The program works with a SQLite database, meaning the changes are saved persistently.
""".format(HelpCommand.getSelect(), HelpCommand.getUpdate(), HelpCommand.getInsert(), HelpCommand.getDelete(), HelpCommand.getUpdateColumn()))

    @staticmethod
    def getInsert():
        return """-i [known|unknown]    Insert a new entry into the specified table (known or unknown).
        For known: provide 'name' and 'mac'.
        For unknown: provide 'ip' and 'mac'."""

    @staticmethod
    def getDelete():
        return """-d [known|unknown]    Delete a row from the specified table (known or unknown) by column value.
        Specify the column name and value for deletion."""

    @staticmethod
    def getUpdate():
        return """-u [known|unknown]    Update the specified table (known or unknown) based on ARP scan."""

    @staticmethod
    def getSelect():
        return """-s [known|unknown]    Show all entries from the specified table (known or unknown)."""
    
    @staticmethod
    def getUpdateColumn():
        return """-uc [known|unknown] [whereColumn] [whereValue] [column] [value]    Update a specific column in the specified table (known or unknown)."""


class UpdateCommand(Command):
    def __init__(self, knownTable, unknownTable, networker, TableUpdater):
        self.tableUpdater = TableUpdater(knownTable, unknownTable, networker)

    def execute(self, args=None):
        self.tableUpdater.deleteOldUnknownEntry()

        if not args:
            self.tableUpdater.updateKnownEntry()
            self.tableUpdater.updateUnknownEntry()
            return 1

        elif args[0] == 'known':
            self.tableUpdater.updateKnownEntry()
        elif args[0] == 'unknown':
            self.tableUpdater.updateUnknownEntry()

        else:
            print(HelpCommand.getUpdate())
            print(f'Invalid table: {args[0]}')

class SelectCommand(Command):
    def __init__(self, knownTable, unknownTable):
        self.knownTable = knownTable
        self.unknownTable = unknownTable

    def execute(self, args=None):
        if not args:
            self.unknownTable.select()
            self.knownTable.select()
            return 1

        table = Command.getCommandTable(args[0], HelpCommand.getSelect, self)

        if table:
            table.select()

class DeleteCommand(Command):
    def __init__(self, knownTable, unknownTable):
        self.knownTable = knownTable
        self.unknownTable = unknownTable

    def execute(self, args):
        if not len(args) == 3:
            print(HelpCommand.getDelete())
            print('Invalid args')
            return 0

        table = Command.getCommandTable(args[0], HelpCommand.getDelete, self)

        if not table:
            return 0

        try:
            table.deleteRowByColumn(args[1], args[2])
        except:
            print(HelpCommand.getDelete())
            print('Invalid options')
            return 0

class InsertCommand(Command):
    def __init__(self, knownTable, unknownTable):
        self.knownTable = knownTable
        self.unknownTable = unknownTable

    def execute(self, args):
        if not len(args) == 3:
            print(HelpCommand.getInsert())
            print('Invalid args')
            return 0

        table = args[0]
        nameIp = args[1]
        mac = args[2]

        table = Command.getCommandTable(table, HelpCommand.getInsert, self)

        if table:
            try:
                table.insertRow(nameIp, mac)
            except Exception as e:
                print(HelpCommand.getInsert())
                print(f'Invalid options: {e}')

class UpdateColumnCommand(Command):
    def __init__(self, knownTable, unknownTable):
        self.knownTable = knownTable
        self.unknownTable = unknownTable

    def execute(self, args):
        if not len(args) == 5:
            print('Invalid args')
            return 0

        table = args[0]
        whereColumn = args[1]
        whereValue = args[2]
        column = args[3]
        value = args[4]

        table = Command.getCommandTable(table, HelpCommand.getUpdateColumn, self)

        if table:
            try:
                table.updateColumnValueByColumn(whereColumn, whereValue, column, value)
            except:
                print(HelpCommand.getUpdateColumn())

class NetworkInfoCommand(Command):
    def __init__(self, NetworkInfo):
        self.networkInfo = NetworkInfo

    def execute(self):
        self.networkInfo.getNotDatabaseEntry()

class CommandDispatcher:
    def __init__(self, database, Table, Networker, TableUpdater, NetworkInfo):
        self.knownTable = Table(database.getKnownTableName(), 1, database.getCursor(), database.getConnection())
        self.unknownTable = Table(database.getUnknownTableName(), 0, database.getCursor(), database.getConnection())

        self.networker = Networker()
        self.networkInfo = NetworkInfo(self.knownTable, self.unknownTable)

        self.commands = {
            '-h': HelpCommand(),
            '-u': UpdateCommand(self.knownTable, self.unknownTable, self.networker, TableUpdater),
            '-s': SelectCommand(self.knownTable, self.unknownTable),
            '-i': InsertCommand(self.knownTable, self.unknownTable),
            '-d': DeleteCommand(self.knownTable, self.unknownTable),
            '-uc': UpdateColumnCommand(self.knownTable, self.unknownTable),
            '-ni': NetworkInfoCommand(self.networkInfo),
        }

    def dispatch(self):
        sysArgs = sys.argv
        if len(sysArgs) > 1:
            command = sysArgs[1]
            
            if command in self.commands:
                commandClass = self.commands[command]
            else:
                print(f'Unknown command: {command}')
                return 0

            args = None if not len(sysArgs) > 2 else sysArgs[2:len(sysArgs)]

            if args:
                commandClass.execute(args)
            else:
                commandClass.execute()

        else:
            print("Missing command.")

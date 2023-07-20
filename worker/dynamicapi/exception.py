class SQLParseException(Exception):
    def __init__(self, message):
        super("SQL 解析错误，请检查 SQL 是否正确，报错：" + message)

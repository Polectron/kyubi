from kyubi.fields import Field
from kyubi.table import Table


class UserTable(Table):
    class Meta(Table.Meta):
        table_name = "test_table"

    id = Field("id")
    name = Field("name")
    age = Field("age")

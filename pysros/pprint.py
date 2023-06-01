# Copyright 2021-2023 Nokia

from .wrappers import *
from .errors import *

__all__ = ("TreePrinter", "printTree", "Column", "Padding", "Table", "KeyValueTable", )

__doc__ = """This module contains functions to assist with stylized
formatting of data.

.. reviewed by PLM 20211201
.. reviewed by TechComms 20211202
"""

def _signalLast(iterable):
    iterable = iter(iterable)
    try:
        ret_var = next(iterable)
        for val in iterable:
            yield False, ret_var
            ret_var = val
        yield True, ret_var
    except StopIteration:
        pass

def _groupByTwo(it):
    while True:
        try:
            yield (next(it), next(it))
        except StopIteration:
            break

class TreePrinter:
    """Object used to print the result of a call
    to :py:meth:`pysros.management.Datastore.get` as an ASCII tree.

    :param align: Whether to align values of a container in the same column.
    :type align: bool
    :param depth: Maximum tree depth to print.
    :type depth: None, int
    :raises ValueError: Error if the depth is not positive.


    .. note::
       The :py:meth:`pysros.pprint.printTree` function provides a
       simple way to use this object.

    .. Reviewed by PLM 20211201
    .. Reviewed by TechComms 20211202
    """
    def __init__(self, *, align=False, depth=None):
        self.align = bool(align)
        self.depth = int(depth) if depth is not None else None

        if self.depth is not None and depth <= 0:
            raise make_exception(pysros_err_depth_must_be_positive)

    def print(self, obj):
        """Print the specified object.

        :param obj: Object to print.

        .. Reviewed by PLM 20210625
        .. Reviewed by TechComms 20210705
        """
        self._printItem(obj, [])

    def _printItem(self, item, branches):
        if isinstance(item, LeafList) or isinstance(item, list):
            self._printLeafList(item)
        elif isinstance(item, Container) or isinstance(item, dict):
            self._printContainer(item, branches)
        else:
            self._printLeaf(item)

    def _printLeaf(self, leaf):
        print(str(leaf))

    def _printLeafList(self, leaflist):
        print(str(leaflist))

    def _printContainer(self, container, branches):
        if self.depth and len(branches) >= self.depth:
            print("{...}")
            return

        if len(branches) > 0:
            print("")

        padding = max([len(key) for key in container.keys()], default=0) if self.align else 0
        for last,(key,value) in _signalLast(container.items()):
            if isinstance(value, list):
                for list_last,value in _signalLast(value):
                    self._printKeyValue(key, value, last and list_last, branches, padding)
            else:
                self._printKeyValue(key, value, last, branches, padding)

    def _printKeyValue(self, key, value, last, branches, padding):
        for branch in branches:
            print(branch, end='')
        print("`-- " if last else "+-- ", end='')
        print("{:<{padding}}: ".format(str(key), padding=padding), end='')
        branches.append("    " if last else "|   ")
        self._printItem(value, branches)
        branches.pop()

def printTree(obj, **kwargs):
    """Print the result of a call to :py:meth:`pysros.management.Datastore.get`
    as an ASCII tree.

    See arguments of :class:`.TreePrinter`

    .. code-block:: python
       :caption: Example
       :name: pysros-pprint-printTree-example-usage
       :emphasize-lines: 8

       from pysros.pprint import printTree
       from pysros.wrappers import Leaf, Container

       def main():
           data = Container({'auto-config-save': Leaf(True),
                             'capabilities': Container({'candidate': Leaf(True),
                             'writable-running': Leaf(False)}), 'admin-state': Leaf('enable')})
           printTree(data)

       if __name__ == "__main__":
           main()

    .. Reviewed by PLM 20211201
    .. Reviewed by TechComms 20211202
    """
    TreePrinter(**kwargs).print(obj)

class Column:
    """Column descriptor to be used in :class:`pysros.pprint.Table`
    and :class:`pysros.pprint.KeyValueTable`.

    :param width: Width of the column (number of characters).
    :type width: int
    :param name: Name of the column. This may be None when column
                 headers are not to be printed. Default None.
    :type name: None, str
    :param align: Alignment of the column: '<' for left, '>' for right
                  and '^' for centered.  Defaults to '<'.
    :type align: str
    :param padding: Number of padding characters, already accounted
                    for in width.  Default 0.
    :type padding: int
    :raises ValueError: Error if align is not valid.

    .. Reviewed by PLM 20211201
    .. Reviewed by TechComms 20211202
    """
    def __init__(self, width, name=None, align='<', padding=0):
        if align != '<' and align != '>' and align != '^':
            raise make_exception(pysros_err_invalid_align, align=align)
        self.name     = name
        self.width    = width
        self.align    = align
        self.padding  = padding
        self._padstr  = " " * padding
        self._format  = self._make_format()

    def _make_format(self):
        return "{{}}{{:{}{}s}}".format(self.align, self.width - self.padding)

    def format(self, value):
        """Format a value according to the parameters of this column,
        considering width, alignment, and padding.

        :param value: Value to format.
        :return: Formatted value.
        :rtype: str

        .. Reviewed by PLM 20210628
        .. Reviewed by TechComms 20210712

        """
        return self._format.format(self._padstr, value)

    @staticmethod
    def create(arg):
        """Static method to create a Column object.

        :param arg: This can either be a :py:class:`pysros.pprint.Column` object or the parameters to pass to the
                    constructor thereof.
        :type arg: :py:class:`pysros.pprint.Column`, tuple
        :raises TypeError: Error if Column is not valid.

        .. Reviewed by PLM 20210628
        .. Reviewed by TechComms 20210712

        """
        if isinstance(arg, Column):
            return arg
        elif isinstance(arg, tuple):
            return Column(*arg)
        else:
            raise make_exception(pysros_err_invalid_col_description)

class Padding(Column):
    """Special type of column which takes no data.  It is only used to add empty space into a table.

    :param width: Width of the (empty) column.
    :type width: int

    .. Reviewed by PLM 20210628
    .. Reviewed by TechComms 20210705

    """
    def __init__(self, width):
        super().__init__(width, padding=width)

class ATable:
    """Abstract parent class for Table and KeyValueTable containing the common functionality.

    .. Reviewed by PLM 20210628
    .. Reviewed by TechComms 20210712
    """
    def __init__(self, title, width=79):
        self._title      = title
        self._width      = width
        self._double     = "=" * self._width
        self._single     = "-" * self._width
        self.reset()

    def reset(self):
        self._numRows   = 0
        self._truncated = False

    def printDoubleLine(self):
        """Print a double line."""
        print(self._double)

    def printSingleLine(self):
        """Print a single line."""
        print(self._single)

    def printHeader(self, title, minor=False):
        """Print a header: text surrounded by single or double lines.

        :param title: Text of the header.
        :param minor: Style of the lines: minor corresponds with single line instead of double.

        .. Reviewed by TechComms 20211013
        """
        line = self.printSingleLine if minor else self.printDoubleLine
        line()
        print(title)
        line()

    def printFooter(self, minor=False):
        """Print the footer.
        This part of the table indicates if any text in the table was truncated.

        :param minor: Style of the lines: minor corresponds with single line instead of double.

        .. Reviewed by TechComms 20211013
        """
        line = self.printSingleLine if minor else self.printDoubleLine
        line()
        if self._truncated:
            print("* indicates that the corresponding row element may have been truncated.")

    def _prepareValue(self, value, col):
        s = str(value)
        if col.padding + len(s) > col.width:
            self._truncated = True
            s = s[:col.width-col.padding-1]+"*"
        return col.format(s)

class Table(ATable):
    """Class that provides the functionality to display tabulated data in the standard SR OS style.

    :param title: Title of the table.
    :type title: str
    :param columns: List of column descriptions. Elements of the list can
                    be a :py:class:`pysros.pprint.Column` or a tuple with
                    parameters to be passed to :py:meth:`pysros.pprint.Column.create`.
    :param width: Width of the table in characters.
    :type width: int
    :param showCount: Indicate if a count of rows should be shown in the footer.
                      In case no count is required, pass in None.
                      In case a count is required, pass in the name of the object
                      represented in a row.
    :param summary: Optional block of text to be displayed in the footer.
    :type summary: str

    .. code-block:: python
       :caption: Example creation of a Table object
       :name: pysros-pprint-Table-example-usage
       :emphasize-lines: 11

       from pysros.pprint import Table, Padding

       def simple_table_builder_example():
           summary = \\
           \"\"\"
       This is the text that we would like in our summary sections
       at the end of the output\"\"\"
           rows = [["row0col0", "row0col1"], ["row1col0", "row1col1"]]
           cols = [(30, "Column0"), (30, "Column1")]
           width = sum([col[0] for col in cols])
           table = Table("This is my tables title", columns=cols,
                         showCount="CounterName", summary=summary, width=width)
           return table, rows

       if __name__ == "__main__":
           table, rows = simple_table_builder_example()

    .. Reviewed by PLM 20211201
    .. Reviewed by TechComms 20211202
    """
    def __init__(self, title, columns, width=79, showCount=None, summary=None):
        super().__init__(title, width=width)
        self._columns   = list(map(Column.create, columns))
        self._showCount = showCount
        self._summary   = summary


    def print(self, rows):
        """
        Display a complete table when passed in the rows of data.
        Separate components are displayed as configured during initialization.

        :param rows: List of tuples containing the data to be displayed. Each tuple in the list is a row
                     and each item in the tuple is the value for a specific column. Padding columns do not
                     need corresponding values in the tuple.

        .. code-block:: python
           :caption: Example :py:meth:`.Table.print` using the Table defined in
                     this :ref:`pysros-pprint-Table-example-usage`
           :name: pysros-pprint-Table-print-example-usage

           >>> def table_print_example(table, rows):
           ...     table.print(rows)
           ...
           >>> table_print_example(table, rows)
           ============================================================
           This is my tables title
           ============================================================
           Column0                        Column1
           ------------------------------------------------------------
           row0col0                       row0col1
           row1col0                       row1col1
           ------------------------------------------------------------
           No. of CounterName: 2

           This is the text that we would like in our summary sections
           at the end of the output
           ============================================================


        .. Reviewed by PLM 20210629
        .. Reviewed by TechComms 20210712
        """
        self.reset()
        if self._title is not None and len(self._title) > 0:
            self.printHeader(self._title)
        else:
            self.printDoubleLine()
        self.printColumnHeaders()
        self.printRows(rows)
        if self._showCount is not None or self._summary is not None:
            self.printSummary(customSummary=self._summary)
        self.printFooter()

    def printRows(self, rows):
        """Print rows of data.

        :param rows: List of tuples containing the data to be displayed. Each tuple in the list is a row
                     and each item in the tuple is the value for a specific column. Padding columns do not
                     need corresponding values in the tuple.

        .. code-block:: python
           :caption: Example :py:meth:`.Table.printRows` using the Table defined in
                     this :ref:`pysros-pprint-Table-example-usage`
           :name: pysros-pprint-Table-printRows-example-usage

           >>> def table_printRows_example(table, rows):
           ...     table.printRows(rows)
           ...
           >>> table_printRows_example(table, rows)
           row0col0                       row0col1
           row1col0                       row1col1

        .. Reviewed by PLM 20210629
        .. Reviewed by TechComms 20210712
        """
        for row in rows:
            self.printRow(row)

    def printRow(self, row):
        """Print a specific row of data.

        :param row: Tuple where each item in the tuple is the value for a specific column. Padding columns do not
                    need corresponding values in the tuple.

        .. code-block:: python
           :caption: Example :py:meth:`.Table.printRow` using the Table defined in
                     this :ref:`pysros-pprint-Table-example-usage`
           :name: pysros-pprint-Table-printRow-example-usage

           >>> def table_printRow_example(table, row):
           ...     table.printRow(row)
           ...
           >>> table_printRow_example(table, rows[0])
           row0col0                       row0col1

        .. Reviewed by PLM 20210629
        .. Reviewed by TechComms 20210712
        """
        width = self._width
        row_iter = iter(row)
        for last,col in _signalLast(self._columns):
            # In case there is no data, or if the column is padding,
            # use the empty string as data
            data = ""
            try:
                if not isinstance(col, Padding):
                    data = next(row_iter)
            except StopIteration:
                pass

            # Format the value using the column formatting
            output = self._prepareValue(data, col)
            length = len(output)

            # Wrap if columns doesn't fit
            if length > width:
                print()
                width = self._width
            elif length == width:
                # Mark as last so we don't append a space
                last = True
                width = 0
            else:
                width -= length

            # Output the formatted value
            print(output, end=('' if last else ' '))

        print()
        self._numRows += 1

    def printColumnHeaders(self):
        """Print the column headers and a separator line.

        .. code-block:: python
           :caption: Example :py:meth:`.Table.printColumnHeaders` using the Table defined in
                     this :ref:`pysros-pprint-Table-example-usage`
           :name: pysros-pprint-Table-printColumnHeaders-example-usage

           >>> def table_printColumnHeaders_example(table):
           ...     table.printColumnHeaders()
           ...
           >>> table_printColumnHeaders_example(table)
           Column0                        Column1
           ------------------------------------------------------------

        .. Reviewed by PLM 20210629
        .. Reviewed by TechComms 20210712
        """
        prevRows = self._numRows
        self.printRow([col.name for col in self._columns if not isinstance(col, Padding)])
        self.printSingleLine()
        self._numRows = prevRows

    def printSummary(self, showLine=True, customSummary=None):
        """Print a summary.
        This section contains the count of rows and any optional summary text.

        :param showLine: Display a line above the summary section.
        :type showLine: bool
        :param customSummary: Custom text to be displayed.
        :type customSummary: str

        .. code-block:: python
           :caption: Example :py:meth:`.Table.printSummary` using the Table defined in
                     this :ref:`pysros-pprint-Table-example-usage`
           :name: pysros-pprint-Table-printSummary-example-usage

           >>> def table_printSummary_example(table):
           ...     table.printSummary(customSummary='This is an optional customized summary')
           ...
           >>> table_printSummary_example(table)
           ------------------------------------------------------------
           No. of CounterName: 0
           This is an optional customized summary

        .. Reviewed by PLM 20210629
        .. Reviewed by TechComms 20210712

        """
        if showLine:
            self.printSingleLine()
        if self._showCount:
            print("No. of {}: {}".format(self._showCount, self._numRows))
        if customSummary is not None:
            print(customSummary)

class KeyValueTable(ATable):
    """Display a list of key and value data in an SR OS table format.

    :param title: Title of the table.
    :type title: str
    :param columns: List of column descriptions. Elements of the list can be :py:class:`pysros.pprint.Column` or
                    a tuple with parameters to be passed to :py:meth:`pysros.pprint.Column.create`.
                    When displaying the data, key and value columns are interleaved.
                    Multiple key-value pairs are allowed on a single row, and the number
                    of columns is even, that is, key and value data always appear on the same row next to each other.
    :param width: Width of the table in characters.
    :raises ValueError: Error if the number of columns is not valid.

    .. code-block:: python
       :caption: Example table creation using :py:class:`.KeyValueTable`
       :name: pysros-pprint-KeyValueTable-example-usage

       >>> from pysros.pprint import KeyValueTable
       >>> table = KeyValueTable('Key Value Table Title', [(20, None), (20, None)])


    .. note::

       This class defines the KeyValueTable object.  The :py:meth:`.KeyValueTable.print`,
       :py:meth:`.KeyValueTable.printKV` or :py:meth:`.KeyValueTable.printKVs` methods should
       be used to output KeyValueTables.


    .. Reviewed by PLM 20210710
    .. Reviewed by TechComms 20210713
    """
    def __init__(self, title, columns, width=79):
        super().__init__(title, width=width)
        self._columns = list(map(Column.create, columns))
        self._check()

    def _check(self):
        if len([None for c in self._columns if not isinstance(c, Padding)]) % 2 != 0:
            raise make_exception(pysros_err_even_num_of_columns_required)

    def _printIter(self, item_iter):
        col_iter = iter(_signalLast(self._columns))
        last_col = False
        last_data = True
        while not last_col:
            last_col,key_col = next(col_iter)

            # print padding-columns
            if isinstance(key_col, Padding):
                print(self._prepareValue("", key_col), end=('' if last_col else ' '))
                continue

            # In case there is no data, stop printing
            try:
                last_data,(key,value) = next(item_iter)
            except StopIteration:
                break

            # also fetch the value-column
            last_col, value_col = next(col_iter)

            # format both key and value
            print(self._prepareValue(key, key_col), end='')
            print(": ", end='')
            print(self._prepareValue(value, value_col), end=('' if last_col else ' '))

        print()
        return not last_data

    def printKV(self, *kvs):
        """Print a table of key-value pairs that are passed into this method.
        This method does not require the data to be structured as a list of 2-tuples.
        The key-value pairs are displayed in the available columns if the pairs
        are available in the :py:class:`.KeyValueTable` definition.

        :param args: Interleaved key and value objects.

        .. code-block:: python
           :caption: Example table output using :py:class:`.KeyValueTable` and :py:meth:`.KeyValueTable.printKV`.
           :name: pysros-pprint-KeyValueTable-printKV-example-usage

           >>> from pysros.pprint import KeyValueTable
           >>> table = KeyValueTable(None, [(20, None), (20, None)])
           >>> table.printKV("k0", "v0", "k1", "v1", "k2", "v2")
           k0                  : v0
           >>> table = KeyValueTable(None, [(12,), (12,), (12,), (12,), (12,), (12,)])
           >>> table.printKV("k0", "v0", "k1", "v1", "k2", "v2")
           k0          : v0           k1          : v1           k2          : v2

        .. Reviewed by PLM 20210710
        .. Reviewed by TechComms 20210713
        """
        item_iter = _signalLast(_groupByTwo(iter(kvs)))
        self._printIter(item_iter)

    def printKVs(self, items):
        """Print a table of key-value pairs that are passed into this method as a list of 2-tuples.

        :param data: List of tuples containing the data to be displayed.
                     Each tuple in the list must contain two fields: (key, value).
                     Data is spread over the available columns first, starting a new row when required.

        .. code-block:: python
           :caption: Example table output using :py:class:`.KeyValueTable` and :py:meth:`.KeyValueTable.printKVs`.
           :name: pysros-pprint-KeyValueTable-printKVs-example-usage

           >>> from pysros.pprint import KeyValueTable
           >>> table = KeyValueTable(None, [(20, None), (20, None)])
           >>> table.printKVs([("k0", "v0"), ("k1", "v1"), ("k2", "v2")])
           k0                  : v0
           k1                  : v1
           k2                  : v2
           >>> table = KeyValueTable(None, [(12,), (12,), (12,), (12,), (12,), (12,)])
           >>> table.printKVs([("k0", "v0"), ("k1", "v1"), ("k2", "v2")])
           k0          : v0           k1          : v1           k2          : v2

        .. Reviewed by PLM 20210710
        .. Reviewed by TechComms 20210713

        """
        item_iter = _signalLast(items)
        while self._printIter(item_iter):
            pass

    def print(self, data):
        """Display a complete table when passed in the list of key-value pairs.
        Separate components are displayed as configured during initialization.

        :param data: List of tuples containing the data to be displayed.
                     Each tuple in the list must contain two fields: (key, value).
                     Data is spread over the available columns first, starting a new row when required.

        .. code-block:: python
           :caption: Example table output using :py:class:`.KeyValueTable` and :py:meth:`.KeyValueTable.print`.
           :name: pysros-pprint-KeyValueTable-print-example-usage

           >>> from pysros.pprint import KeyValueTable
           >>> data = [('k0','v0'), ('k1','v1'),('k2','v2')]
           >>> table = KeyValueTable('Two column Key Value Table Title', [(20, None), (20, None)])
           >>> table.print(data)
           ===============================================================================
           Two column Key Value Table Title
           ===============================================================================
           k0                  : v0
           k1                  : v1
           k2                  : v2
           ===============================================================================
           >>> table = KeyValueTable('Six column Key Value Table Title',
           ...                       [(12,), (12,), (12,), (12,), (12,), (12,)])
           >>> table.print(data)
           ===============================================================================
           Six column Key Value Table Title
           ===============================================================================
           k0          : v0           k1          : v1           k2          : v2
           ===============================================================================

        .. Reviewed by PLM 20210710
        .. Reviewed by TechComms 20210713
        """
        self.reset()
        if self._title is not None and len(self._title) > 0:
            self.printHeader(self._title)
        else:
            self.printDoubleLine()
        self.printColumnHeaders()
        self.printKVs(data)
        self.printFooter()

    def printColumnHeaders(self):
        """Print the column headers and a separator line.

        .. code-block:: python
           :caption: Example :py:meth:`.KeyValueTable.printColumnHeaders` using the Table defined in
                     this :ref:`pysros-pprint-Table-example-usage`
           :name: pysros-pprint-KeyValueTable-printColumnHeaders-example-usage

           >>> def table_printColumnHeaders_example(table):
           ...     table.printColumnHeaders()
           ...
           >>> table_printColumnHeaders_example(table)
           Column0                        Column1
        """
        if any(col.name for col in self._columns):
            self.printKV(*[col.name for col in self._columns])
            self.printSingleLine()


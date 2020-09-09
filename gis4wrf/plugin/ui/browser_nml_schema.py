from typing import Tuple, Set, Any
import html

from PyQt5.QtWidgets import QTextBrowser

class NmlSchemaBrowser(QTextBrowser):
    def __init__(self, nml_schema: dict):
        super().__init__()
        html, self.anchors = get_schema_html(nml_schema)
        # TODO set encoding of help page, e.g. degree symbol appears incorrect
        self.setText(html)

def to_fortran(val: Any) -> str:
    if val is True:
        return '.true.'
    if val is False:
        return '.false.'
    if isinstance(val, str):
        val = f"'{val}'"
    return str(val)

def get_schema_html(nml_schema: dict) -> Tuple[str, Set[str]]:
    nml_html = '<html>'
    anchors = set() # type: Set[str]
    for section_name, section in nml_schema.items():
        anchors.add(section_name)
        nml_html += f'<h2><a name="{section_name}">&{section_name}</a></h2>'
        for var_name, variable in section.items():
            anchors.add(var_name)
            description = variable['description']
            type_ = variable['type']
            item_type = variable.get('itemtype')
            min_len = variable.get('minlen')
            min_ = variable.get('min')
            max_ = variable.get('max')
            if item_type:
                type_label += f' of {item_type}'
            else:
                type_label = type_
            default = variable.get('default')
            example = variable.get('example')
            options = variable.get('options')

            nml_html += f'<h3><a name="{var_name}">{var_name}</a></h3>'
            nml_html += f'<p>{html.escape(description)}</p>'
            nml_html += f'Type: {type_}<br>'
            if min_len is not None:
                if isinstance(min_len, str):
                    min_len = f'<a href="#{min_len}">{min_len}</a>'
                nml_html += f'Length: {min_len}<br>'
            if min_ is not None:
                nml_html += f'Min: <code>{min_}</code><br>'
            if max_ is not None:
                nml_html += f'Max: <code>{max_}</code><br>'
            if default is not None:
                default_ = to_fortran(default)
                if type_ == 'list':
                    if default == []:
                        nml_html += f'Default: empty list'
                    else:
                        nml_html += f'Default: list of <code>{html.escape(default_)}</code>'
                else:
                    nml_html += f'Default: <code>{html.escape(default_)}</code><br>'
            if example is not None:
                val_type = item_type if item_type else type_
                if isinstance(example, str) and val_type != 'str':
                    # Here we have a literal example in Fortran syntax,
                    # so we avoid surrounding it with single quotes.
                    pass
                else:
                    example = to_fortran(example)
                nml_html += f'Example: <code>{html.escape(example)}</code><br>'
            if options:
                if isinstance(options, list):
                    nml_html += f'Options: <code>{html.escape(", ".join(map(to_fortran, options)))}</code><br>'
                else:
                    nml_html += '<br>Options: <table border=1>'
                    for val, description in options.items():
                        val = to_fortran(val)
                        nml_html += f'<tr><td width="30%" align="center"><code>{html.escape(val)}</code></td>'
                        nml_html += f'<td width="70%">{html.escape(description)}</td></tr>'
                    nml_html += '</table>'

    nml_html += '</html>'
    return nml_html, anchors

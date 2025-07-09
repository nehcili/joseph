import inspect
import smtplib
from email.mime.text import MIMEText
from typing import Union
import nbformat
from nbconvert import HTMLExporter
import os
from nbconvert.preprocessors import ExecutePreprocessor
from datetime import datetime


def get_all_args(include_implicit_args: bool = False) -> dict:
    """
    Get all arguments of the caller function, excluding 'self' or 'cls' if include_implicit_args is False.

    Args:
        include_implicit_args (bool): If True, include 'self' or 'cls' in the returned dictionary.

    Returns:
        dict: Dictionary of argument names and their values.
    """
    frame = inspect.currentframe()
    outer_frame = frame.f_back  # Get the caller's frame
    args, _, _, values = inspect.getargvalues(outer_frame)
    res = {arg: values[arg] for arg in args}

    if not include_implicit_args:
        # Remove 'self' or 'cls' if present
        res.pop('self', None)
        res.pop('cls', None)

    return res


def send_email(
    subject: str,
    from_addr: str,
    to_addrs: list[str],
    content: Union[str, MIMEText],
    password: str = None,
    html: bool = False,
    smtp_server: str = 'smtp.gmail.com',
    smtp_port: int = 465
):
    """
    Send an email with the given subject, from, to, and content.

    Args:
        subject (str): Email subject.
        from_addr (str): Sender email address.
        to_addrs (list[str]): List of recipient email addresses.
        content (str or MIMEText): Email content (plain text or HTML).
        password (str, optional): Password for the sender email account.
        html (bool, optional): If True, send as HTML. Otherwise, send as plain text.
        smtp_server (str, optional): SMTP server address.
        smtp_port (int, optional): SMTP server port.
    """
    if html:
        msg = MIMEText(content, 'html')
    else:
        msg = MIMEText(content)

    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = ', '.join(to_addrs)

    with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
        server.login(from_addr, password)
        server.sendmail(from_addr, to_addrs, msg.as_string())


def run_and_save_notebook(
    input_path: str,
    output_folder: str,
    remove_input: bool = False,
    suffix: str = None,
) -> tuple[str, str]:
    """
    Executes a Jupyter notebook and saves the output notebook and HTML file.

    Args:
        input_path (str): Path to the input notebook file.
        output_folder (str): Folder to save the output files.
        remove_input (bool): If True, remove input code cells in the HTML output.

    Returns:
        tuple[str, str]: Paths to the output notebook and HTML files.
    """
    # Load the notebook
    with open(input_path, 'r', encoding='utf-8') as f:
        nb = nbformat.read(f, as_version=4)

    # Execute the notebook
    ep = ExecutePreprocessor(timeout=600, kernel_name='python3')
    ep.preprocess(nb, {'metadata': {'path': os.path.dirname(input_path)}})

    # Prepare output file names
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_nb_name = f"{base_name}_{timestamp}.ipynb"
    output_html_name = f"{base_name}_{timestamp}.html"
    output_nb_path = os.path.join(output_folder, output_nb_name)
    output_html_path = os.path.join(output_folder, output_html_name)

    # Save the executed notebook
    with open(output_nb_path, 'w', encoding='utf-8') as f:
        nbformat.write(nb, f)

    # Export to HTML
    html_exporter = HTMLExporter()
    if remove_input:
        html_exporter.exclude_input = True
    (body, resources) = html_exporter.from_notebook_node(nb)
    with open(output_html_path, 'w', encoding='utf-8') as f:
        f.write(body)

    return output_nb_path, output_html_path


def run_and_save_notebook_with_args(
    input_path: str,
    output_folder: str,
    inject_args: dict = None,
    remove_input: bool = False,
    suffix: str = None,
) -> tuple[str, str]:
    """
    Executes a Jupyter notebook with injected arguments and saves the output notebook and HTML file.

    Args:
        input_path (str): Path to the input notebook file.
        output_folder (str): Folder to save the output files.
        inject_args (dict, optional): Arguments to inject into the notebook as a code cell at the top.
        remove_input (bool): If True, remove input code cells in the HTML output.

    Returns:
        tuple[str, str]: Paths to the output notebook and HTML files.

    Useage:
    =======
    In jupyter notebook, you can use the injected arguments like this. get_arg is a method that will be
    inserted at the top of the notebook when the notebook is run. You don't need to define it yourself 
    nor import it.

    example_arg = get_arg('example_arg', default='default_value')
    example_int = get_arg('example_int')
    example_list = get_arg('example_list')
    example_dict = get_arg('example_dict')
    """
    # Load the notebook
    with open(input_path, 'r', encoding='utf-8') as f:
        nb = nbformat.read(f, as_version=4)

    # Inject arguments as a new code cell at the top
    def _set_args(**kwargs):
        code = [
            "def get_arg(name, default=None):\n\tkwargs = {\n"
        ]
        for key, value in kwargs.items():
            code.append(
                f"\t\t'{key}': {repr(value)},\n"
            )
        code.append("\t}\n")
        code.append("\treturn kwargs.get(name, default)\n")
        return ''.join(code)

    if inject_args:
        arg_lines = _set_args(**inject_args)
        arg_cell = nbformat.v4.new_code_cell(arg_lines)
        nb.cells.insert(0, arg_cell)

    # Execute the notebook
    ep = ExecutePreprocessor(timeout=600, kernel_name='python3')
    ep.preprocess(nb, {'metadata': {'path': os.path.dirname(input_path)}})

    # Prepare output file names
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_nb_name = f"{base_name}_{timestamp}.ipynb"
    output_html_name = f"{base_name}_{timestamp}.html"
    output_nb_path = os.path.join(output_folder, output_nb_name)
    output_html_path = os.path.join(output_folder, output_html_name)

    # Save the executed notebook
    with open(output_nb_path, 'w', encoding='utf-8') as f:
        nbformat.write(nb, f)

    # Export to HTML
    html_exporter = HTMLExporter()
    if remove_input:
        html_exporter.exclude_input = True
    (body, resources) = html_exporter.from_notebook_node(nb)
    with open(output_html_path, 'w', encoding='utf-8') as f:
        f.write(body)

    return output_nb_path, output_html_path

if __name__ == "__main__":
    run_and_save_notebook_with_args(
        input_path='/Users/lichen/code/projects/joseph/.notebooks/scratches/scratch_v1.ipynb',
        output_folder='/Users/lichen/code/projects/joseph/.notebooks/outputs/',
        inject_args={
            'example_arg': 'example_value',
            'example_int': 42,
            'example_list': [1, 2, 3],
            'example_dict': {'key1': 'value1', 'key2': 'value2'}
        },
        remove_input=True
    )
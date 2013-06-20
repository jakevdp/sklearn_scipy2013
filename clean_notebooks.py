"""Utility script to be used to cleanup the notebooks before git commit"""

import sys
import os
import io
from IPython.nbformat import current
try:
    from IPython.kernel import KernelManager
    assert KernelManager  # to silence pyflakes
except ImportError:
    # 0.13
    from IPython.zmq.blockingkernelmanager import BlockingKernelManager
    KernelManager = BlockingKernelManager


def remove_outputs(nb):
    """Remove the outputs from a notebook"""
    for ws in nb.worksheets:
        for cell in ws.cells:
            if cell.cell_type == 'code':
                cell.outputs = []
                if 'prompt_number' in cell:
                    del cell['prompt_number']


def run_notebook(nb):
    km = KernelManager()
    km.start_kernel(stderr=open(os.devnull, 'w'))
    kc = km.client() if hasattr(km, 'client') else km
    kc.start_channels()
    shell = kc.shell_channel
    # simple ping:
    shell.execute("pass")
    shell.get_msg()

    cells = 0
    failures = 0
    for ws in nb.worksheets:
        for cell in ws.cells:
            if cell.cell_type != 'code':
                continue
            shell.execute(cell.input)
            # wait for finish, maximum 5min
            reply = shell.get_msg(timeout=300)['content']
            if reply['status'] == 'error':
                failures += 1
                print "\nFAILURE:"
                print cell.input
                print '-----'
                print "raised:"
                print '\n'.join(reply['traceback'])
            cells += 1
            sys.stdout.write('.')

    print
    print "ran notebook %s" % nb.metadata.name
    print "    ran %3i cells" % cells
    if failures:
        print "    %3i cells raised exceptions" % failures
    kc.stop_channels()
    km.shutdown_kernel()
    del km


def clean_notebook_file(fname, do_check=False):
    print("Removing outputs for: " + fname)
    orig_wd = os.getcwd()
    with io.open(fname, 'rb') as f:
        nb = current.read(f, 'json')

    if do_check:
        os.chdir(os.path.dirname(fname))
        run_notebook(nb)
    remove_outputs(nb)

    os.chdir(orig_wd)
    with io.open(fname, 'wb') as f:
        nb = current.write(nb, f, 'json')


if __name__ == '__main__':
    args = sys.argv[1:]
    targets = [t for t in args if not t.startswith('--')]
    do_check = '--check' in args
    if not targets:
        targets = [os.path.join(os.path.dirname(__file__), 'notebooks')]

    for target in targets:
        if os.path.isdir(target):
            fnames = [os.path.abspath(os.path.join(target, f))
                      for f in os.listdir(target)
                      if f.endswith('.ipynb')]
        else:
            fnames = [target]
        for fname in fnames:
            clean_notebook_file(fname, do_check=do_check)

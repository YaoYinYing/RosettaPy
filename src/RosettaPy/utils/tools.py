import contextlib
import shutil
import tempfile
import time
import os
from typing import Optional


@contextlib.contextmanager
def timing(msg: str):
    print(f"Started {msg}")
    tic = time.time()
    yield
    toc = time.time()
    print(f"Finished {msg} in {toc - tic:.3f} seconds")


@contextlib.contextmanager
def tmpdir_manager(base_dir: Optional[str] = None):
    """Context manager that deletes a temporary directory on exit."""
    tmpdir = tempfile.mkdtemp(dir=base_dir)
    try:
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


@contextlib.contextmanager
def isolate(save_to: str = "./save", base_dir: Optional[str] = None):
    """Context manager that isolate threads from file system."""
    save_to = os.path.abspath(save_to)
    tmpdir = tempfile.mkdtemp(dir=base_dir)
    curdir = os.getcwd()  # save current directory path
    os.chdir(tmpdir)  # change to tmp dir
    try:
        yield
    finally:
        os.chdir(curdir)  # change back to previous curdir
        shutil.move(tmpdir, save_to)  # move any files to target dir

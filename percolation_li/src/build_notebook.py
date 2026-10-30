"""Execute the current explanatory notebook without overwriting manual edits."""
import nbformat as nbf
from .core import PART
from .check_environment import check_environment


def execute(path):
    check_environment()
    import os
    import sys
    from jupyter_client import KernelManager
    from nbclient import NotebookClient
    # A private kernel command avoids registering kernels or editing global config.
    local_env = {
        "JUPYTER_CONFIG_DIR":str(PART/"work/jupyter_config"),
        "JUPYTER_DATA_DIR":str(PART/"work/jupyter_data"),
        "JUPYTER_RUNTIME_DIR":str(PART/"work/jupyter_runtime"),
        "IPYTHONDIR":str(PART/"work/ipython"),
        "MPLCONFIGDIR":str(PART/"work/matplotlib"),
        "PYTHONDONTWRITEBYTECODE":"1"}
    os.environ.update(local_env)
    from jupyter_client.kernelspec import KernelSpec
    spec = KernelSpec(argv=[sys.executable,"-m","ipykernel_launcher","-f","{connection_file}"],
                      display_name="PC5253-KG (Python 3.11.16)",language="python")
    runtime = PART/"work/jupyter_runtime"
    runtime.mkdir(parents=True,exist_ok=True)
    manager = KernelManager(kernel_name="pc5253-kg",transport="tcp" if os.name == "nt" else "ipc",
                            connection_file=str(runtime/"notebook-kernel.json"))
    manager._kernel_spec = spec
    notebook = nbf.read(path,as_version=4)
    client = NotebookClient(notebook,km=manager,timeout=120,
                            resources={"metadata":{"path":str(PART)}})
    try:
        client.execute()
    finally:
        if manager.has_kernel:
            manager.shutdown_kernel(now=True)
    nbf.validate(notebook)
    nbf.write(notebook,path)
    print(f"Executed and saved {len(notebook.cells)} notebook cells.")


if __name__ == "__main__":
    import sys
    path = PART/"percolation_research.ipynb"
    nbf.validate(nbf.read(path, as_version=4))
    if "--execute" in sys.argv:
        execute(path)

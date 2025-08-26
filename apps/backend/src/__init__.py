"""Package marker for the backend source package used by imports like
`from src...` inside the container.

This file can remain empty, but having it ensures `src` is a proper Python
package when the code is executed inside Docker and when sys.path includes
the parent directory.
"""

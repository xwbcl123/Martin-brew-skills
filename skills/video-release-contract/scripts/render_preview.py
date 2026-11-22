import sys
from package import command

if __name__ == "__main__":
    raise SystemExit(command(["render_preview", *sys.argv[1:]]))

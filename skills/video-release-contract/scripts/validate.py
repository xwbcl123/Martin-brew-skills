import sys
from package import command

if __name__ == "__main__":
    raise SystemExit(command(["validate", *sys.argv[1:]]))

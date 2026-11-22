import sys
from package import command

if __name__ == "__main__":
    raise SystemExit(command(["seal", *sys.argv[1:]]))

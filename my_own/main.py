from .filecheck import FileCheck
import sys









def main():
    try:
        FileCheck.validate_map(sys.argv)
    except BaseException as e:
        print(f"ERROR: {e}")
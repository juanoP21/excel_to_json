import sys
from pdfconvert import process_and_send


def main():
    if len(sys.argv) < 3:
        print("Usage: python webhook_client.py <bank_key> <file_path>")
        sys.exit(1)
    bank_key = sys.argv[1]
    file_path = sys.argv[2]
    with open(file_path, "rb") as f:
        data = f.read()
    process_and_send(bank_key, file_path, data)


if __name__ == "__main__":
    main()

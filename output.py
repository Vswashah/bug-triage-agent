def print_report(text: str):
    """Pretty-print the triage report to terminal."""
    if "---TRIAGE REPORT---" in text:
        before, report = text.split("---TRIAGE REPORT---", 1)
        report = report.split("---END REPORT---")[0]

        if before.strip():
            print(before.strip())

        print("\n" + "="*50)
        print("         BUG TRIAGE REPORT")
        print("="*50)
        print(report.strip())
        print("="*50 + "\n")
    else:
        print(text)
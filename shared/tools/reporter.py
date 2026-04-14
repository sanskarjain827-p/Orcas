# Reporter tools for Orcas agents
def generate_report(title, content):
    import os
    report_path = os.path.expanduser(f"~/orcas-reports/{title}.md")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        f.write(f"# {title}\n\n{content}")
    return report_path

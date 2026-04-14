# System tools for Orcas agents
def get_system_stats():
    import psutil
    return {
        "cpu": psutil.cpu_percent(),
        "memory": psutil.virtual_memory().percent
    }

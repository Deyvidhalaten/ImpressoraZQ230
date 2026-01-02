_jobs = {}

def save(job):
    _jobs[job.job_id] = job
    return job

def find_by_id(job_id):
    return _jobs.get(job_id)

def find_pending_by_loja(loja):
    return [
        job for job in _jobs.values()
        if job.loja == loja and job.status == "queued"
    ]
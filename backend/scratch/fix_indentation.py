import sys
import os

def fix_applications():
    path = 'backend/app/api/applications.py'
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return
        
    with open(path, 'r') as f:
        lines = f.readlines()
    
    # We target the range 950 to 1181 (1-indexed)
    head = lines[:949]
    tail = lines[1181:]
    
    body = [
        "@router.get(\"\", response_model=ApplicationListResponse, response_class=ORJSONResponse)\n",
        "def get_hr_applications(\n",
        "    job_id: int = None,\n",
        "    from_date: str = None,\n",
        "    to_date: str = None,\n",
        "    status: str = None,\n",
        "    time_range: str = None,\n",
        "    search: str = None,\n",
        "    skip: int = 0,\n",
        "    limit: int = 20,\n",
        "    current_user: User = Depends(get_current_hr),\n",
        "    db: Session = Depends(get_db)\n",
        "):\n",
        "    \"\"\"Get all applications for HR's jobs (HR only)\"\"\"\n",
        "    t_start = time.perf_counter()\n",
        "    items = []\n",
        "    total = 0\n",
        "    safe_skip = max(0, int(skip or 0))\n",
        "    safe_limit = max(1, min(int(limit or 20), 100))\n",
        "    \n",
        "    try:\n",
        "        # 1. Base Query with optimized loading\n",
        "        query = db.query(Application).options(\n",
        "            joinedload(Application.job).load_only(Job.id, Job.title, Job.hr_id, Job.status, Job.job_id),\n",
        "            joinedload(Application.resume_extraction).load_only(\n",
        "                ResumeExtraction.id, ResumeExtraction.resume_score,\n",
        "                ResumeExtraction.skill_match_percentage, ResumeExtraction.experience_level,\n",
        "                ResumeExtraction.summary, ResumeExtraction.extracted_skills,\n",
        "            ),\n",
        "            load_only(\n",
        "                Application.id, Application.candidate_name, Application.candidate_email,\n",
        "                Application.status, Application.applied_at, Application.file_status,\n",
        "                Application.candidate_photo_path, Application.resume_file_path,\n",
        "                Application.resume_score, Application.composite_score\n",
        "            ),\n",
        "            joinedload(Application.interview).load_only(Interview.id, Interview.status, Interview.overall_score),\n",
        "        ).outerjoin(Job)\n",
        "\n",
        "        # 2. Filters\n",
        "        if job_id:\n",
        "            query = query.filter(Application.job_id == job_id)\n",
        "\n",
        "        if status and status != 'all':\n",
        "            if status == \"applied\":\n",
        "                query = query.filter(Application.status.in_((\"applied\", \"submitted\")))\n",
        "            else:\n",
        "                query = query.filter(Application.status == status)\n",
        "\n",
        "        if search and str(search).strip():\n",
        "            term = f\"%{search}%\"\n",
        "            query = query.filter(or_(\n",
        "                Application.candidate_name.ilike(term),\n",
        "                Application.candidate_email.ilike(term),\n",
        "                Job.title.ilike(term)\n",
        "            ))\n",
        "\n",
        "        if from_date:\n",
        "            try:\n",
        "                sd = datetime.strptime(from_date, \"%Y-%m-%d\").date()\n",
        "                query = query.filter(func.date(func.timezone(\"UTC\", Application.applied_at)) >= sd)\n",
        "            except ValueError: pass\n",
        "        if to_date:\n",
        "            try:\n",
        "                ed = datetime.strptime(to_date, \"%Y-%m-%d\").date()\n",
        "                query = query.filter(func.date(func.timezone(\"UTC\", Application.applied_at)) <= ed)\n",
        "            except ValueError: pass\n",
        "\n",
        "        # 3. Security\n",
        "        if current_user.role != \"super_admin\":\n",
        "            query = query.filter(or_(Application.hr_id == current_user.id, Job.hr_id == current_user.id))\n",
        "\n",
        "        # 4. Retrieval\n",
        "        total = query.count()\n",
        "        applications = query.order_by(Application.applied_at.desc()).offset(safe_skip).limit(safe_limit).all()\n",
        "\n",
        "        # Path sanitization\n",
        "        for app in applications:\n",
        "            for field in ['candidate_photo_path', 'resume_file_path']:\n",
        "                val = getattr(app, field)\n",
        "                if val and \"uploads\" in val:\n",
        "                    idx = val.find(\"uploads\")\n",
        "                    setattr(app, field, val[idx:].replace(\"\\\\\", \"/\"))\n",
        "\n",
        "        # 5. Response Mapping\n",
        "        t_map_start = time.perf_counter()\n",
        "        items = [build_application_summary_response(app) for app in applications]\n",
        "        t_map_duration = time.perf_counter() - t_map_start\n",
        "        \n",
        "        duration = time.perf_counter() - t_start\n",
        "        import logging; logger = logging.getLogger(__name__)\n",
        "        logger.info(f\"PERFORMANCE_TRACE: get_hr_applications total={duration:.4f}s (Map: {t_map_duration:.4f}s)\")\n",
        "        \n",
        "        pages = (total + safe_limit - 1) // safe_limit\n",
        "        return {\n",
        "            \"items\": items,\n",
        "            \"total\": total,\n",
        "            \"page\": (safe_skip // safe_limit) + 1,\n",
        "            \"size\": safe_limit,\n",
        "            \"pages\": pages\n",
        "        }\n",
        "    except Exception as e:\n",
        "        import logging; logger = logging.getLogger(__name__)\n",
        "        logger.error(f\"APPLICATION_API_ERROR: {str(e)}\", exc_info=True)\n",
        "        return {\"items\": [], \"total\": 0, \"page\": 1, \"size\": safe_limit, \"pages\": 0, \"error_hint\": str(e)}\n"
    ]
    
    with open(path, 'w') as f:
        f.writelines(head + body + tail)
    print("Applications fixed.")

def fix_search():
    path = 'backend/app/api/search.py'
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return
        
    with open(path, 'r') as f:
        lines = f.readlines()
    
    # Range 23 to 206
    head = lines[:22]
    tail = lines[206:]
    
    body = [
        "async def search_candidates(\n",
        "    payload: dict = Body(...),\n",
        "    db: Session = Depends(get_db),\n",
        "    current_hr = Depends(get_current_hr)\n",
        "):\n",
        "    query_text = payload.get(\"query\")\n",
        "    skip = int(payload.get(\"skip\", 0))\n",
        "    limit = int(payload.get(\"limit\", 30))\n",
        "    if not query_text: raise HTTPException(status_code=400, detail=\"Search query is required\")\n",
        "    \n",
        "    try:\n",
        "        filters = await decompose_search_query(query_text)\n",
        "        query = db.query(Application).options(\n",
        "            joinedload(Application.resume_extraction).load_only(\n",
        "                ResumeExtraction.id, ResumeExtraction.resume_score, ResumeExtraction.skill_match_percentage, ResumeExtraction.experience_level,\n",
        "                ResumeExtraction.summary, ResumeExtraction.extracted_skills, ResumeExtraction.years_of_experience, ResumeExtraction.reasoning, ResumeExtraction.previous_roles\n",
        "            ),\n",
        "            joinedload(Application.job).load_only(Job.id, Job.title, Job.job_id),\n",
        "            load_only(Application.id, Application.candidate_name, Application.status, Application.applied_at, Application.composite_score, Application.resume_score, Application.file_status, Application.candidate_photo_path),\n",
        "            defer(Application.candidate_phone), defer(Application.hr_notes)\n",
        "        )\n",
        "        if current_hr.role != 'super_admin': query = query.filter(Application.hr_id == current_hr.id)\n",
        "        \n",
        "        keyword_conditions = []\n",
        "        for field in [\"tech_skills\", \"soft_skills\", \"role_keywords\"]:\n",
        "            for val in filters.get(field, []):\n",
        "                keyword_conditions.append(or_(ResumeExtraction.extracted_skills.ilike(f\"%{val}%\"), ResumeExtraction.extracted_text.ilike(f\"%{val}%\"), Job.title.ilike(f\"%{val}%\")))\n",
        "        if keyword_conditions: query = query.filter(and_(*keyword_conditions))\n",
        "        \n",
        "        total = query.count()\n",
        "        results = query.order_by(Application.composite_score.desc()).offset(skip).limit(limit).all()\n",
        "        \n",
        "        search_results = []\n",
        "        for app in results:\n",
        "            search_results.append({\n",
        "                \"id\": app.id, \"candidate_name\": app.candidate_name, \"current_status\": app.status,\n",
        "                \"job_title\": app.job.title if app.job else \"General Portfolio\", \"job_id\": app.job.job_id if app.job else \"N/A\",\n",
        "                \"resume_score\": max(0.0, min(100.0, app.resume_score or 0.0)), \"composite_score\": max(0.0, min(100.0, app.composite_score or 0.0)),\n",
        "                \"years_of_experience\": app.resume_extraction.years_of_experience if app.resume_extraction else 0,\n",
        "                \"match_insight\": app.resume_extraction.reasoning if app.resume_extraction else \"Historical match.\",\n",
        "                \"skills\": app.resume_extraction.extracted_skills if app.resume_extraction else \"[]\",\n",
        "                \"applied_at\": app.applied_at.isoformat() if app.applied_at else None,\n",
        "                \"file_status\": app.file_status\n",
        "            })\n",
        "        return {\"metadata\": {\"total\": total, \"skip\": skip, \"limit\": limit}, \"candidates\": search_results}\n",
        "    except Exception as e:\n",
        "        import logging; logger = logging.getLogger(__name__)\n",
        "        logger.error(f\"SEARCH_API_ERROR: {str(e)}\", exc_info=True)\n",
        "        return {\"metadata\": {\"total\": 0, \"error_hint\": str(e)}, \"candidates\": []}\n"
    ]
    
    with open(path, 'w') as f:
        f.writelines(head + body + tail)
    print("Search fixed.")

if __name__ == "__main__":
    fix_applications()
    fix_search()

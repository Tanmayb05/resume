You are a job description parser. Extract structured information from the job description below.

## Job Description

{{ jd_text }}

## Instructions

Extract the following fields. If a field is not mentioned in the JD, use null for strings and [] for arrays.

## Output Format

Return a valid JSON object with this exact structure:

```json
{
  "company": "<company name>",
  "role": "<job title>",
  "location": "<city, state or Remote — list multiple if given>",
  "employment_type": "<full-time | internship | contract>",
  "department": "<department or team name, or null>",
  "description": "<1-3 sentence role summary>",
  "responsibilities": ["<responsibility>"],
  "requirements": ["<must-have requirement>"],
  "qualifications": ["<preferred or nice-to-have qualification>"],
  "skills": {
    "technical": ["<technical skill>"],
    "soft": ["<soft skill>"]
  },
  "education": ["<education requirement>"],
  "experience_required": "<experience level or null>",
  "benefits": ["<benefit>"],
  "salary_range": "<salary range string or 'Not disclosed'>",
  "date_posted": "<date string or null>",
  "application_deadline": "<date string or null>",
  "visa_keywords": ["<exact visa/sponsorship phrases found in the JD>"]
}
```

Rules:
- company, role, and location are required — infer from context if not explicit.
- employment_type must be exactly one of: full-time, internship, contract.
- visa_keywords: copy exact phrases from the JD related to visa, sponsorship, work authorization, citizenship requirements.
- Do not include any text outside the JSON block.

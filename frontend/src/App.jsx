import React, { useEffect, useRef, useState } from 'react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000/recommend';
const API_BASE_URL = API_URL.replace(/\/recommend\/?$/, '');
const INCOME_CAP_NOTICE = 250000;
const RESULTS_PAGE_SIZE = 10;
const SAVED_SCHOLARSHIPS_KEY = 'ai-grant-finder:saved-scholarships';
const DASHBOARD_HASHES = new Set(['#home', '#deadline-heading', '#saved-heading']);

function getPageFromHash(hash) {
  return DASHBOARD_HASHES.has(hash) ? 'home' : 'profile';
}

const initialProfile = {
  age: '',
  income: '',
  education: '',
  field: '',
  gender: '',
  category: '',
  state: '',
  marks: '',
};

const initialFilters = {
  search_text: '',
  provider_type: '',
  level: '',
  deadline_status: '',
  sort_by: 'relevance',
};

const statesAndUnionTerritories = [
  'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh', 'Goa', 'Gujarat',
  'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka', 'Kerala', 'Madhya Pradesh',
  'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'Odisha', 'Punjab',
  'Rajasthan', 'Sikkim', 'Tamil Nadu', 'Telangana', 'Tripura', 'Uttar Pradesh',
  'Uttarakhand', 'West Bengal', 'Andaman and Nicobar Islands', 'Chandigarh',
  'Dadra and Nagar Haveli and Daman and Diu', 'Delhi', 'Jammu and Kashmir', 'Ladakh',
  'Lakshadweep', 'Puducherry',
];

const studyBranchGroups = [
  {
    label: 'Computing and digital technology',
    options: [
      'Computer Science and Engineering', 'Computer Engineering', 'Computer Science',
      'Software Engineering', 'Information Technology', 'Information Systems',
      'Artificial Intelligence and Machine Learning', 'Artificial Intelligence and Data Science',
      'Data Science and Analytics', 'Cybersecurity', 'Cloud Computing', 'Internet of Things',
      'Big Data Engineering and Analytics', 'Blockchain Technology', 'Computer Networks and Security',
      'Computer Applications (BCA / MCA)', 'Embedded Systems and IoT', 'VLSI Design and Technology',
      'Quantum Computing', 'AR / VR and Game Development', 'Bioinformatics', 'Computational Biology',
      'FinTech', 'Human-Computer Interaction', 'Digital Forensics',
    ],
  },
  {
    label: 'Engineering and applied technology',
    options: [
      'Aerospace Engineering', 'Agricultural Engineering', 'Automobile Engineering',
      'Chemical Engineering', 'Civil Engineering', 'Construction Technology',
      'Electrical and Electronics Engineering', 'Electrical Engineering',
      'Electronics and Communication Engineering', 'Environmental Engineering',
      'Food Technology', 'Industrial and Production Engineering',
      'Instrumentation and Control Engineering', 'Marine Engineering', 'Materials Engineering',
      'Mechanical Engineering', 'Mechatronics Engineering', 'Metallurgical Engineering',
      'Mining Engineering', 'Nanotechnology', 'Petroleum Engineering', 'Polymer Technology',
      'Production Engineering', 'Renewable Energy Engineering', 'Robotics and Automation',
      'Structural Engineering', 'Textile Technology',
    ],
  },
  {
    label: 'Health and life sciences',
    options: [
      'Biochemistry', 'Biomedical Engineering', 'Biotechnology', 'Dentistry (BDS)',
      'Genetics', 'Life Sciences', 'Medicine (MBBS)', 'Microbiology', 'Nursing',
      'Occupational Therapy', 'Pharmacy', 'Physiotherapy', 'Public Health',
      'Veterinary Science',
    ],
  },
  {
    label: 'Natural sciences and mathematics',
    options: [
      'Applied Mathematics', 'Biology', 'Chemistry', 'Mathematics and Computing',
      'Physics', 'Statistics', 'Statistics and Data Analytics',
    ],
  },
  {
    label: 'Agriculture and environment',
    options: [
      'Agriculture', 'Agricultural Sciences', 'Dairy Technology', 'Environmental Science',
      'Fisheries Science', 'Forestry', 'Horticulture',
    ],
  },
  {
    label: 'Business, arts, and other degrees',
    options: [
      'Accounting and Finance', 'Architecture', 'Business Administration (BBA / MBA)',
      'Commerce and Management', 'Design and Fine Arts', 'Economics', 'Education and Teaching',
      'Hospitality and Hotel Management', 'Humanities and Social Sciences', 'Law',
      'Media and Communication', 'Psychology', 'Public Policy', 'Social Work', 'Other',
    ],
  },
];

const fields = [
  { name: 'age', label: 'Age', type: 'number', placeholder: 'e.g. 20', min: '15', max: '100' },
  { name: 'income', label: 'Annual family income (INR)', type: 'number', placeholder: 'e.g. 250000', min: '0' },
  { name: 'education', label: 'Current education', type: 'select', placeholder: 'Choose education level', options: ['UG', 'Diploma', 'PG', 'PhD', 'Other'] },
  { name: 'field', label: 'Course / branch', type: 'select', placeholder: 'Choose your course or branch', groups: studyBranchGroups },
  { name: 'gender', label: 'Gender', type: 'select', placeholder: 'Choose gender', options: ['Female', 'Male', 'Other', 'Prefer not to say'] },
  { name: 'category', label: 'Category', type: 'select', placeholder: 'Choose category', options: ['General', 'OBC', 'SC', 'ST', 'EWS', 'Minority', 'Persons with Disabilities', 'Other'] },
  { name: 'state', label: 'State / union territory', type: 'select', placeholder: 'Choose your state or UT', options: statesAndUnionTerritories },
  { name: 'marks', label: 'Marks / CGPA', type: 'text', placeholder: 'e.g. 82% or 8.4 CGPA' },
];

function isSpecified(value) {
  return Boolean(value) && !['not specified', 'programme-specific', 'scheme-specific', 'any'].includes(value.trim().toLowerCase());
}

function formatIncomeLimit(value) {
  const amountMatch = value.match(/[\d,]+(?:\.\d+)?/);
  if (!amountMatch) return `Family income: ${value}`;

  const amount = Number(amountMatch[0].replace(/,/g, ''));
  const limit = `₹${amount.toLocaleString('en-IN')}`;
  return /under|below|less than/i.test(value)
    ? `Family income under ${limit}`
    : `Family income up to ${limit}`;
}

function getEligibility(scholarship) {
  const details = [];
  if (isSpecified(scholarship.level)) details.push(scholarship.level);
  if (isSpecified(scholarship.field)) details.push(scholarship.field);
  if (isSpecified(scholarship.gender)) details.push(scholarship.gender);
  if (isSpecified(scholarship.category)) details.push(scholarship.category);
  if (isSpecified(scholarship.max_income)) {
    details.push(formatIncomeLimit(scholarship.max_income));
  }
  if (isSpecified(scholarship.min_percentage)) {
    details.push(`${scholarship.min_percentage}% minimum marks`);
  }
  if (isSpecified(scholarship.age_requirement)) {
    details.push(`Age ${scholarship.age_requirement}`);
  }
  return details.length ? details.join(' · ') : scholarship.description || 'Check the official page for eligibility details.';
}

function App() {
  const [profile, setProfile] = useState(initialProfile);
  const [filters, setFilters] = useState(initialFilters);
  const [recommendations, setRecommendations] = useState([]);
  const [visibleRecommendationCount, setVisibleRecommendationCount] = useState(RESULTS_PAGE_SIZE);
  const [savedScholarships, setSavedScholarships] = useState([]);
  const [savedScholarshipsReady, setSavedScholarshipsReady] = useState(false);
  const [savedScholarshipsError, setSavedScholarshipsError] = useState('');
  const [dashboard, setDashboard] = useState(null);
  const [dashboardError, setDashboardError] = useState('');
  const [dashboardLoading, setDashboardLoading] = useState(true);
  const [dashboardRetry, setDashboardRetry] = useState(0);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');
  const [profileError, setProfileError] = useState('');
  const resultsPanelRef = useRef(null);
  const [currentPage, setCurrentPage] = useState(() => getPageFromHash(window.location.hash));

  useEffect(() => {
    function syncPageWithHash() {
      setCurrentPage(getPageFromHash(window.location.hash));
    }

    window.addEventListener('hashchange', syncPageWithHash);
    return () => window.removeEventListener('hashchange', syncPageWithHash);
  }, []);

  useEffect(() => {
    let active = true;
    setDashboardLoading(true);
    setDashboardError('');
    axios.get(`${API_BASE_URL}/dashboard`)
      .then((response) => {
        if (active) setDashboard(response.data);
      })
      .catch((requestError) => {
        if (active) {
          setDashboardError(
            requestError.response?.data?.error || 'Dashboard data is unavailable. Check that the Flask API is running.',
          );
        }
      })
      .finally(() => {
        if (active) setDashboardLoading(false);
      });
    return () => { active = false; };
  }, [dashboardRetry]);

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(SAVED_SCHOLARSHIPS_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (!Array.isArray(parsed)) {
          throw new Error('Saved scholarship data must be a list.');
        }
        setSavedScholarships(parsed.filter((scholarship) => scholarship && scholarship.id && scholarship.name));
      }
    } catch (storageError) {
      setSavedScholarshipsError('Saved scholarships could not be loaded from this browser.');
      console.error('Unable to load saved scholarships:', storageError);
    } finally {
      setSavedScholarshipsReady(true);
    }
  }, []);

  useEffect(() => {
    if (!savedScholarshipsReady) return;
    try {
      window.localStorage.setItem(SAVED_SCHOLARSHIPS_KEY, JSON.stringify(savedScholarships));
      setSavedScholarshipsError('');
    } catch (storageError) {
      setSavedScholarshipsError('Your browser could not store saved scholarships. Check its storage settings.');
      console.error('Unable to save scholarships:', storageError);
    }
  }, [savedScholarships, savedScholarshipsReady]);

  function updateProfile(event) {
    const { name, value } = event.target;
    setProfile((current) => ({ ...current, [name]: value }));
    setRecommendations([]);
    setVisibleRecommendationCount(RESULTS_PAGE_SIZE);
    setStatus('idle');
    setError('');
    setProfileError('');
  }

  function updateFilters(event) {
    const { name, value } = event.target;
    const updatedFilters = { ...filters, [name]: value };
    setFilters(updatedFilters);
    setRecommendations([]);
    setVisibleRecommendationCount(RESULTS_PAGE_SIZE);
    setStatus('idle');
    setError('');

    if (name !== 'search_text' && fields.every(({ name: fieldName }) => profile[fieldName].trim())) {
      searchScholarships(profile, updatedFilters);
    }
  }

  function toggleSavedScholarship(scholarship) {
    setSavedScholarships((current) => (
      current.some((saved) => String(saved.id) === String(scholarship.id))
        ? current.filter((saved) => String(saved.id) !== String(scholarship.id))
        : [...current, scholarship]
    ));
  }

  async function searchScholarships(searchProfile, searchFilters = filters) {
    const missingFields = fields.filter(({ name }) => !searchProfile[name].trim());
    if (missingFields.length) {
      setRecommendations([]);
      setVisibleRecommendationCount(RESULTS_PAGE_SIZE);
      setStatus('idle');
      setError('');
      setProfileError(`Complete your profile before searching. Missing: ${missingFields.map(({ label }) => label).join(', ')}.`);
      window.requestAnimationFrame(() => {
        document.getElementsByName(missingFields[0].name)[0]?.focus();
      });
      return;
    }

    setStatus('loading');
    setError('');
    setProfileError('');
    setRecommendations([]);
    setVisibleRecommendationCount(RESULTS_PAGE_SIZE);

    const query = Object.entries(searchProfile)
      .filter(([, value]) => value.trim())
      .map(([key, value]) => `${key}: ${value}`)
      .join(', ');

    const hasFilters = Object.values(searchFilters).some((value) => value && value !== 'relevance');
    if (!query && !hasFilters) {
      setError('Add a profile detail or an advanced search filter to find scholarships.');
      setStatus('error');
      return;
    }

    try {
      const response = await axios.post(API_URL, { query, profile: searchProfile, filters: searchFilters, top_n: 50 });
      setRecommendations(response.data.recommendations || []);
      setStatus('success');
      window.requestAnimationFrame(() => {
        resultsPanelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    } catch (requestError) {
      setError(
        requestError.response?.data?.error ||
          `Could not reach the scholarship service. Make sure Flask is running at ${API_URL}.`,
      );
      setStatus('error');
    }
  }

  function findScholarships(event) {
    event.preventDefault();
    searchScholarships(profile);
  }

  return (
    <main className="portal-shell">
      <header className="topbar">
        <div className="page-shell topbar-inner">
          <a className="brand" href="#home" aria-label="Scholarship Finder home">
            <span className="brand-mark" aria-hidden="true">SF</span>
            <span>Scholarship Finder</span>
          </a>
          <nav className="topnav" aria-label="Main navigation">
            {currentPage === 'home' ? (
              <>
                <a href="#deadline-heading">Deadlines</a>
                <a className="topnav-action" href="#profile">Build profile <span aria-hidden="true">↗</span></a>
              </>
            ) : (
              <>
                <a href="#home">Home</a>
                <a href="#profile-heading">Student profile</a>
              </>
            )}
          </nav>
        </div>
      </header>

      {currentPage === 'home' ? (
        <>
          <section className="intro" id="home">
            <div className="intro-inner">
              <div className="intro-main">
                <p className="eyebrow"><span className="eyebrow-mark" aria-hidden="true">✳</span> AI GRANT & SCHOLARSHIP FINDER</p>
                <h1>Make your next<br /><span>move affordable.</span></h1>
                <p className="intro-copy">Explore government and private awards matched to your course, background, and study goals.</p>
                <a className="intro-action" href="#profile">Build your profile <span aria-hidden="true">↓</span></a>
              </div>
              <aside className="intro-meta" aria-label="Scholarship directory overview">
                <div className="academic-year"><span>ACADEMIC YEAR</span><strong>2026<span>–</span>27</strong></div>
                <div className="intro-divider" />
                <div className="directory-stats">
                  <div><strong>{dashboard?.total_scholarships ?? '—'}</strong><span>listed awards</span></div>
                  <div><strong>{dashboard?.deadline_counts?.closing_soon ?? '—'}</strong><span>closing soon</span></div>
                </div>
                <p className="meta-footnote">Deadline information from the scholarship directory</p>
              </aside>
            </div>
          </section>

          <section className="page-shell dashboard-section" aria-labelledby="deadline-heading">
            <div className="home-section-heading">
              <div>
                <p className="step-label">SCHOLARSHIP DASHBOARD</p>
                <h2 id="deadline-heading">Deadlines to watch</h2>
              </div>
              <a className="all-courses-link" href="#profile">Search all awards <span aria-hidden="true">↗</span></a>
            </div>
            {dashboardError && (
              <div className="dashboard-connection" role="status">
                <p className="dashboard-error">{dashboardError}</p>
                <button className="text-button" type="button" onClick={() => setDashboardRetry((retry) => retry + 1)}>
                  Retry connection
                </button>
              </div>
            )}
            {savedScholarshipsError && <p className="dashboard-error" role="status">{savedScholarshipsError}</p>}
            {dashboard && (
              <>
                <div className="dashboard-metrics">
                  <div><span>Open or closing</span><strong>{dashboard.deadline_counts.open + dashboard.deadline_counts.closing_soon}</strong></div>
                  <div><span>Closing within 14 days</span><strong>{dashboard.deadline_counts.closing_soon}</strong></div>
                  <div><span>Opening soon</span><strong>{dashboard.deadline_counts.upcoming}</strong></div>
                  <div><span>Past deadline</span><strong>{dashboard.deadline_counts.closed}</strong></div>
                </div>
                {dashboard.upcoming_deadlines.length ? (
                  <div className="deadline-list">
                    {dashboard.upcoming_deadlines.map((item) => (
                      <article className="deadline-item" key={item.id}>
                        <div><strong>{item.name}</strong><span>{item.provider}</span></div>
                        <div className="deadline-item-date">
                          <strong>{item.application_deadline}</strong>
                          <span className={item.deadline_status === 'Closing soon' ? 'closing-soon' : ''}>
                            {item.days_remaining === 0 ? 'Due today' : `${item.days_remaining} days remaining`}
                          </span>
                        </div>
                        <div className="deadline-item-links">
                          {item.application_url && (
                            <a className="apply-link" href={item.application_url} target="_blank" rel="noreferrer">Apply <span aria-hidden="true">↗</span></a>
                          )}
                          {item.guidelines_url && (
                            <a className="guidelines-link" href={item.guidelines_url} target="_blank" rel="noreferrer">Details</a>
                          )}
                        </div>
                      </article>
                    ))}
                  </div>
                ) : <p className="dashboard-empty">No upcoming deadlines are listed in the dataset.</p>}
              </>
            )}
            <section className="saved-section" aria-labelledby="saved-heading">
              <div className="home-section-heading">
                <div>
                  <p className="step-label">YOUR SHORTLIST</p>
                  <h2 id="saved-heading">Saved scholarships <span className="saved-count">{savedScholarships.length}</span></h2>
                </div>
                <a className="all-courses-link" href="#profile">Find more <span aria-hidden="true">↗</span></a>
              </div>
              {savedScholarships.length ? (
                <div className="deadline-list">
                  {savedScholarships.map((scholarship) => (
                    <article className="deadline-item saved-item" key={scholarship.id}>
                      <div>
                        <strong>{scholarship.name}</strong>
                        <span>{scholarship.provider || 'Scholarship provider'} · Deadline: {scholarship.application_deadline || 'Not listed'}</span>
                      </div>
                      <div className="saved-item-actions">
                        {scholarship.application_url && (
                          <a className="apply-link" href={scholarship.application_url} target="_blank" rel="noreferrer">Apply <span aria-hidden="true">↗</span></a>
                        )}
                        <button className="text-button" type="button" onClick={() => toggleSavedScholarship(scholarship)}>Remove</button>
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <p className="dashboard-empty">Save a scholarship from your recommendations and it will stay on this device for later.</p>
              )}
            </section>
          </section>
        </>
      ) : (
        <>
          <section className="page-shell profile-page-head">
            <a className="back-link" href="#home"><span aria-hidden="true">←</span> Main page</a>
            <div className="profile-head-copy">
              <p className="step-label">PERSONALIZED SCHOLARSHIP SEARCH</p>
              <h1 className="profile-route-title">Build your student profile</h1>
              <p>Share the details that help identify relevant awards.</p>
            </div>
            <span className="profile-year">ACADEMIC YEAR 2026–27</span>
          </section>

          <div className="page-shell content-grid">
            <section className="form-panel" aria-labelledby="profile-heading">
              <div className="section-heading">
                <div>
                  <p className="step-label">01 / YOUR DETAILS</p>
                  <h2 id="profile-heading">Student profile</h2>
                  <p className="profile-form-hint">Complete every field to get recommendations matched to your profile.</p>
                </div>
                <span className="required-note">All fields required</span>
              </div>
              <form onSubmit={findScholarships}>
                <div className="form-grid">
                  {fields.map((field) => (
                    <label className="field" key={field.name}>
                      <span>{field.label} <span className="required-marker" aria-hidden="true">*</span></span>
                      {field.type === 'select' ? (
                        <select name={field.name} value={profile[field.name]} onChange={updateProfile} required>
                          <option value="">{field.placeholder}</option>
                          {field.groups
                            ? field.groups.map((group) => (
                              <optgroup key={group.label} label={group.label}>
                                {group.options.map((option) => <option key={option} value={option}>{option}</option>)}
                              </optgroup>
                            ))
                            : field.options.map((option) => <option key={option} value={option}>{option}</option>)}
                        </select>
                      ) : (
                        <input
                          name={field.name}
                          type={field.type}
                          value={profile[field.name]}
                          onChange={updateProfile}
                          placeholder={field.placeholder}
                          min={field.min}
                          max={field.max}
                          required
                        />
                      )}
                    </label>
                  ))}
                </div>
                <details className="advanced-search">
                  <summary className="advanced-heading">
                    <div><p className="step-label">REFINE RESULTS</p><h3>Advanced search</h3></div>
                    <span>Optional · click to expand</span>
                  </summary>
                  <div className="form-grid">
                    <label className="field">
                      <span>Keyword or interest</span>
                      <input name="search_text" value={filters.search_text} onChange={updateFilters} placeholder="e.g. renewable energy, research" />
                    </label>
                    <label className="field">
                      <span>Provider type</span>
                      <select name="provider_type" value={filters.provider_type} onChange={updateFilters}>
                        <option value="">Any provider</option>
                        <option value="Government">Government</option>
                        <option value="Private">Private</option>
                      </select>
                    </label>
                    <label className="field">
                      <span>Education level</span>
                      <select name="level" value={filters.level} onChange={updateFilters}>
                        <option value="">Any education level</option>
                        {(dashboard?.filter_options?.levels || []).map((level) => (
                          <option key={level} value={level}>{level}</option>
                        ))}
                      </select>
                    </label>
                    <label className="field">
                      <span>Application status</span>
                      <select name="deadline_status" value={filters.deadline_status} onChange={updateFilters}>
                        <option value="">Any deadline</option>
                        <option value="open">Open, including closing soon</option>
                        <option value="closing">Closing within 14 days</option>
                        <option value="upcoming">Opens soon</option>
                        <option value="closed">Past deadline</option>
                      </select>
                    </label>
                    <label className="field">
                      <span>Rank results</span>
                      <select name="sort_by" value={filters.sort_by} onChange={updateFilters}>
                        <option value="relevance">Best profile and text match</option>
                        <option value="deadline">Soonest deadline</option>
                      </select>
                    </label>
                  </div>
                </details>
                {profileError && <p className="profile-validation-error" role="alert">{profileError}</p>}
                <button className="submit-button" type="submit" disabled={status === 'loading'}>
                  <span>{status === 'loading' ? 'Finding matches…' : 'Find scholarships'}</span>
                  <span className="button-arrow" aria-hidden="true">↗</span>
                </button>
              </form>
              <p className="privacy-note">Your details are used to find matches and are not saved by this page.</p>
            </section>

            <section className="results-panel" ref={resultsPanelRef} aria-live="polite" aria-labelledby="results-heading">
              <div className="section-heading results-heading">
                <div>
                  <p className="step-label">02 / YOUR MATCHES</p>
                  <h2 id="results-heading">{status === 'success' ? 'Scholarships for you' : 'Recommendations'}</h2>
                  {status === 'success' && <p className="results-intro">Review each award’s eligibility and deadline on its official page before applying.</p>}
                </div>
                {recommendations.length > 0 && <span className="result-count">{recommendations.length} matches</span>}
              </div>
              {status === 'success' && Number(profile.income) > INCOME_CAP_NOTICE && (
                <p className="income-filter-note">Scholarships with published income limits below your income are excluded.</p>
              )}

              {status === 'idle' && (
                <div className="empty-state"><span className="empty-icon" aria-hidden="true">✳</span><h3>Your matches will appear here</h3><p>Complete the profile and select “Find scholarships” to see recommendations.</p></div>
              )}
              {status === 'loading' && <div className="empty-state"><span className="loader" aria-hidden="true" /><h3>Finding your matches</h3><p>Checking your profile against available scholarships…</p></div>}
              {status === 'error' && <div className="message error-message" role="alert"><strong>We couldn’t get recommendations.</strong><p>{error}</p></div>}
              {status === 'success' && recommendations.length === 0 && <div className="empty-state"><span className="empty-icon" aria-hidden="true">⌕</span><h3>No matches returned</h3><p>Try adding more details to your profile and search again.</p></div>}

              {recommendations.length > 0 && (
                <div className="scholarship-list">
                  {recommendations.slice(0, visibleRecommendationCount).map((scholarship) => (
                    <article className="scholarship-card" key={scholarship.id ?? scholarship.name}>
                      <div className="card-topline">
                        <div className="provider-details">
                          <span className="provider">{scholarship.provider || 'Scholarship provider'}</span>
                          {scholarship.provider_type && <span className="provider-type">{scholarship.provider_type}</span>}
                        </div>
                        <div className="card-actions">
                          <span className="match-score">
                            <strong>{Number(scholarship.match_score ?? scholarship.similarity ?? 0).toFixed(1)}%</strong>
                            <span>match</span>
                          </span>
                          <button
                            className="save-button"
                            type="button"
                            aria-pressed={savedScholarships.some((saved) => String(saved.id) === String(scholarship.id))}
                            onClick={() => toggleSavedScholarship(scholarship)}
                          >
                            {savedScholarships.some((saved) => String(saved.id) === String(scholarship.id)) ? 'Saved' : '＋ Save'}
                          </button>
                        </div>
                      </div>
                      <h3>{scholarship.name}</h3>
                      {scholarship.description && <p className="scholarship-description">{scholarship.description}</p>}
                      <div className="scholarship-tags" aria-label="Scholarship details">
                        {scholarship.field && <span>{scholarship.field}</span>}
                        {scholarship.level && <span>{scholarship.level}</span>}
                        {scholarship.state && !['any', 'all india', 'not specified'].includes(scholarship.state.toLowerCase()) && <span>{scholarship.state}</span>}
                      </div>
                      <details className="eligibility-details">
                        <summary>Eligibility details</summary>
                        <p>{getEligibility(scholarship)}</p>
                      </details>
                      <div className="card-footer">
                        <div className="deadline">
                          <span className={`deadline-status ${scholarship.deadline_status === 'Closing soon' ? 'closing-soon' : ''}`}>
                            {scholarship.deadline_status || 'Not listed'}
                          </span>
                          <strong>{scholarship.application_deadline || 'Deadline not listed'}</strong>
                          {scholarship.days_remaining !== null && scholarship.days_remaining !== undefined && scholarship.days_remaining >= 0 && (
                            <span>{scholarship.days_remaining === 0 ? 'Due today' : `${scholarship.days_remaining} days remaining`}</span>
                          )}
                        </div>
                        <div className="application-links">
                          {scholarship.application_url ? (
                            <a className="apply-link" href={scholarship.application_url} target="_blank" rel="noreferrer">Apply <span aria-hidden="true">↗</span></a>
                          ) : <span className="no-link">Link unavailable</span>}
                          {scholarship.guidelines_url && (
                            <a className="guidelines-link" href={scholarship.guidelines_url} target="_blank" rel="noreferrer">Scheme details</a>
                          )}
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              )}
              {status === 'success' && visibleRecommendationCount < recommendations.length && (
                <button
                  className="show-more-button"
                  type="button"
                  onClick={() => setVisibleRecommendationCount((count) => Math.min(count + RESULTS_PAGE_SIZE, recommendations.length))}
                >
                  Show {Math.min(RESULTS_PAGE_SIZE, recommendations.length - visibleRecommendationCount)} more
                  <span>{visibleRecommendationCount} of {recommendations.length} shown</span>
                </button>
              )}
            </section>
          </div>

          <section className="page-shell profile-discovery" aria-label="Scholarship websites">
            <div className="discovery-panel" id="profile-websites">
              <div className="section-heading">
                <div><p className="step-label">CHECK CURRENT OPPORTUNITIES</p><h2>Scholarship websites</h2></div>
                <span className="required-note">Opens external sites</span>
              </div>
              {dashboardError && (
                <div className="dashboard-connection" role="status">
                  <p className="dashboard-error">{dashboardError}</p>
                  <button className="text-button" type="button" onClick={() => setDashboardRetry((retry) => retry + 1)}>
                    Retry connection
                  </button>
                </div>
              )}
              <div className="website-grid">
                {(dashboard?.scholarship_websites || []).map((site) => (
                  <article className="website-card" key={site.name}>
                    <span className="website-type">{site.type}</span>
                    <h3>{site.name}</h3>
                    <p>{site.description}</p>
                    <a className="apply-link" href={site.url} target="_blank" rel="noreferrer">
                      Visit website <span aria-hidden="true">↗</span>
                    </a>
                  </article>
                ))}
              </div>
              {!dashboardError && dashboardLoading && <p className="dashboard-empty" role="status">Loading scholarship websites…</p>}
              {dashboard && dashboard.scholarship_websites.length === 0 && (
                <p className="dashboard-empty" role="status">No scholarship websites are listed yet.</p>
              )}
              <p className="website-disclaimer">These links open live external websites. This directory does not sync with them, so confirm current deadlines and requirements on each site.</p>
            </div>
          </section>
        </>
      )}

      <footer className="page-shell footer"><span>AI Grant & Scholarship Finder</span><span>Opportunities start with a search.</span></footer>
    </main>
  );
}

export default App;

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak

def create_tp_brochure():
    pdf_path = "data/GNDEC_Bidar_TP_Cell_Brochure.pdf"
    doc = SimpleDocTemplate(pdf_path, pagesize=letter, leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#003366"),
        alignment=1, # Center
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#555555"),
        alignment=1, # Center
        spaceAfter=10
    )
    
    h2_style = ParagraphStyle(
        'Heading2Custom',
        parent=styles['Heading2'],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#003366"),
        spaceBefore=10,
        spaceAfter=4
    )
    
    body_style = ParagraphStyle(
        'BodyCustom',
        parent=styles['Normal'],
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#222222"),
        spaceAfter=4
    )
    
    bullet_style = ParagraphStyle(
        'BulletCustom',
        parent=styles['Normal'],
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#222222"),
        leftIndent=12,
        spaceAfter=3
    )

    story = []
    
    # Title
    story.append(Paragraph("Guru Nanak Dev Engineering College (GNDEC), Bidar", title_style))
    story.append(Paragraph("<b>Training & Placement Cell (T&P Cell) Official Brochure</b>", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#003366"), spaceAfter=10))
    
    # About Section
    story.append(Paragraph("1. Overview & Vision of T&P Cell", h2_style))
    story.append(Paragraph(
        "The Training and Placement Cell at GNDEC Bidar acts as a vital bridge between prestigious industry partners and students. "
        "The Cell is committed to providing 100% career guidance, skill enhancement, and placement assistance. "
        "With state-of-the-art infrastructure including dedicated seminar halls, interview cabins, and online assessment labs, "
        "the T&P Cell ensures smooth conduct of on-campus, pooled-campus, and virtual placement drives.",
        body_style
    ))
    
    # Placement Highlights Table
    story.append(Paragraph("2. Placement Highlights & Statistics", h2_style))
    stats_data = [
        [Paragraph("<b>Key Metric</b>", body_style), Paragraph("<b>Details / Record</b>", body_style)],
        [Paragraph("Placement Track Record", body_style), Paragraph("90%+ Eligible Students Placed", body_style)],
        [Paragraph("Highest Package Offered", body_style), Paragraph("₹12.00 Lakhs Per Annum (12 LPA)", body_style)],
        [Paragraph("Average Package Offered", body_style), Paragraph("₹4.50 Lakhs Per Annum (4.5 LPA)", body_style)],
        [Paragraph("Top Recruiting Tier Packages", body_style), Paragraph("₹6.5 LPA to ₹10.00 LPA", body_style)],
        [Paragraph("Corporate & Recruiting Partners", body_style), Paragraph("150+ Top Companies / 50+ Annual Visiting Recruiters", body_style)],
        [Paragraph("Annual Placement Drives", body_style), Paragraph("Comprehensive On-Campus & Pooled Drives", body_style)]
    ]
    t = Table(stats_data, colWidths=[200, 330])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#e6f0fa")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cccccc")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))
    
    # Recruiters
    story.append(Paragraph("3. Prestigious Recruiters & Industry Partners", h2_style))
    story.append(Paragraph("• <b>IT, Software & Tech Giants:</b> Tata Consultancy Services (TCS), Infosys, Wipro, Cognizant, Accenture, Mindtree, HCL Technologies, L&T Infotech (LTIMindtree), Capgemini, Tech Mahindra, Hexaware Technologies, SLK Software, IBM, Amazon, Quest Global, CoreEL Technologies, Deloitte, Cisco, Bosch, Jio, Paytm, Atos Syntel, Salesforce.", bullet_style))
    story.append(Paragraph("• <b>Core Engineering, Automotive & Infrastructure:</b> Ashok Leyland, JBM Group, Hindustan Unilever, LG Electronics, Nissan, TVS Motors, Cyient, Schneider Electric.", bullet_style))
    story.append(Paragraph("• <b>Banking, Financial Services & Consulting:</b> Axis Bank, Kotak Mahindra Bank, ICICI Bank, HDFC Bank.", bullet_style))
    story.append(Paragraph("• <b>Skill Development & Training Partners:</b> Seventh Sense Talent Solutions, SMART Training Resources India, ICT Academy, CADMAXX, Skill Bout.", bullet_style))
    
    # Training & Skill Development
    story.append(Paragraph("4. Training, Skill Development & Internship Programs", h2_style))
    story.append(Paragraph("• <b>Aptitude & Soft Skills:</b> Comprehensive quantitative aptitude, logical reasoning, verbal ability, and group discussion training starting from 3rd semester onwards.", bullet_style))
    story.append(Paragraph("• <b>Technical & Coding Bootcamps:</b> Hands-on coding in Python, Java, Full Stack Web Development, Cloud Computing, AI/ML, and Data Structures.", bullet_style))
    story.append(Paragraph("• <b>Mock Interviews & Industry Mentorship:</b> Technical and HR mock interviews conducted by alumni and industry leaders.", bullet_style))
    story.append(Paragraph("• <b>Mandatory Internships:</b> 4-8 weeks industry internship facilitation in accordance with VTU curriculum guidelines.", bullet_style))
    
    # Leadership & Contact
    story.append(Paragraph("5. T&P Cell Key Contacts & Leadership", h2_style))
    contact_data = [
        [Paragraph("<b>Role / Designation</b>", body_style), Paragraph("<b>Name / Department</b>", body_style), Paragraph("<b>Contact / Email</b>", body_style)],
        [Paragraph("Training & Placement Officer (TPO)", body_style), Paragraph("Prof. Shravan Kumar", body_style), Paragraph("Phone: +91 6364925581 / +91 9900418224<br/>Email: placement@gndecb.ac.in", body_style)],
        [Paragraph("Assistant Placement Officer", body_style), Paragraph("Prof. Bheem Rao Patil (CSE Dept)", body_style), Paragraph("Email: placement@gndecb.ac.in", body_style)],
        [Paragraph("T&P Faculty Committee", body_style), Paragraph("Dr. Praveen Reddy, Prof. Vimala Kulkarni, Prof. Suresh Patil, Prof. Q Rahman (Mech), Prof. Shivshanker BC, Dr. Mahesh Kumar, Prof. Netra S, Prof. Saqlain, Prof. Kaveri", body_style), Paragraph("T&P Office, GNDEC Bidar Campus", body_style)],
        [Paragraph("Principal Office", body_style), Paragraph("Principal, GNDEC Bidar", body_style), Paragraph("Phone: 08482-226949 / 9741892834<br/>Email: principal@gndecb.ac.in", body_style)]
    ]
    t2 = Table(contact_data, colWidths=[150, 200, 180])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#e6f0fa")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cccccc")),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t2)
    
    doc.build(story)
    print(f"Generated {pdf_path}")

def create_college_brochure():
    pdf_path = "data/GNDEC_Bidar_College_Programs_Facilities.pdf"
    doc = SimpleDocTemplate(pdf_path, pagesize=letter, leftMargin=28, rightMargin=28, topMargin=25, bottomMargin=25)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle2',
        parent=styles['Heading1'],
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#003366"),
        alignment=1,
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle2',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#555555"),
        alignment=1,
        spaceAfter=6
    )
    
    h2_style = ParagraphStyle(
        'Heading2Custom2',
        parent=styles['Heading2'],
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#003366"),
        spaceBefore=6,
        spaceAfter=3
    )
    
    body_style = ParagraphStyle(
        'BodyCustom2',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#222222"),
        spaceAfter=3
    )
    
    bullet_style = ParagraphStyle(
        'BulletCustom2',
        parent=styles['Normal'],
        fontSize=8.2,
        leading=11,
        textColor=colors.HexColor("#222222"),
        leftIndent=10,
        spaceAfter=2
    )

    story = []
    
    # ---------------- PAGE 1: OVERVIEW & 13 DEPARTMENTS ----------------
    story.append(Paragraph("Guru Nanak Dev Engineering College (GNDEC), Bidar", title_style))
    story.append(Paragraph("<b>Academic Departments, Campus Facilities, Research & Online Portals</b>", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.2, color=colors.HexColor("#003366"), spaceAfter=6))
    
    story.append(Paragraph("1. About the Institution & Accreditations", h2_style))
    story.append(Paragraph(
        "Guru Nanak Dev Engineering College (GNDEC), Bidar, Karnataka was established in 1980 under the Guru Nanak Vidyak Society. "
        "It is a <b>NAAC A+ Grade</b> accredited premier institution, approved by AICTE, affiliated to Visvesvaraya Technological University (VTU), Belagavi, "
        "and accredited by NBA. The lush green campus is located on Mailoor Road, Bidar - 585403.",
        body_style
    ))
    
    story.append(Paragraph("2. Academic Departments (Total 13 Departments)", h2_style))
    story.append(Paragraph(
        "Guru Nanak Dev Engineering College (GNDEC), Bidar comprises exactly <b>13 academic departments</b> as listed on the official portal:",
        body_style
    ))
    story.append(Paragraph("1. <b>Department of Civil Engineering:</b> B.E. in Civil Engineering and Ph.D. Research.", bullet_style))
    story.append(Paragraph("2. <b>Department of Computer Science & Engineering:</b> B.E. in CSE, M.Tech in CSE, and Ph.D. Research.", bullet_style))
    story.append(Paragraph("3. <b>Department of Artificial Intelligence & ML:</b> B.E. in Artificial Intelligence & Machine Learning.", bullet_style))
    story.append(Paragraph("4. <b>Department of CSE (AI & ML):</b> B.E. in Computer Science & Engineering (AI & ML).", bullet_style))
    story.append(Paragraph("5. <b>Department of CSE (Data Science):</b> B.E. in Computer Science & Engineering (Data Science).", bullet_style))
    story.append(Paragraph("6. <b>Department of Electrical & Electronics Engineering:</b> B.E. in Electrical & Electronics Engineering (EEE).", bullet_style))
    story.append(Paragraph("7. <b>Department of Electronics & Communication Engineering:</b> B.E. in ECE, M.Tech in Digital Communication, and Ph.D. Research.", bullet_style))
    story.append(Paragraph("8. <b>Department of Information Science & Engineering:</b> B.E. in Information Science & Engineering (ISE).", bullet_style))
    story.append(Paragraph("9. <b>Department of CSE (IoT & CyberSecurity):</b> B.E. in CSE (IoT & Cyber Security).", bullet_style))
    story.append(Paragraph("10. <b>Department of Mechanical Engineering:</b> B.E. in Mechanical Engineering and Ph.D. Research.", bullet_style))
    story.append(Paragraph("11. <b>Department of Applied Sciences & Humanities:</b> Basic sciences including Physics, Chemistry, Mathematics, and Humanities.", bullet_style))
    story.append(Paragraph("12. <b>Department of Master of Business Administration:</b> MBA (Finance, Marketing, HR, Systems).", bullet_style))
    story.append(Paragraph("13. <b>Department of Master of Computer Applications:</b> MCA (2-Year Postgraduate degree).", bullet_style))
    
    # ---------------- PAGE 2: OFFICIAL CAMPUS FACILITIES & SERVICES --------
    story.append(PageBreak())
    
    story.append(Paragraph("3. Official Campus Facilities (From Website Facilities Menu)", h2_style))
    story.append(Paragraph(
        "GNDEC Bidar provides comprehensive student-centric and campus services accessible through the college portal:",
        body_style
    ))
    story.append(Paragraph("• <b>Central Library & Digital Resource Center:</b> Over 60,000+ volumes, subscription to IEEE, ScienceDirect, Springer e-journals, DELNET membership, automated Koha LMS, and 24x7 air-conditioned reading halls.", bullet_style))
    story.append(Paragraph("• <b>Exam Queries:</b> Dedicated Examination Section managing semester exams, VTU notifications, hall tickets, revaluation applications, grade card distribution, and exam grievances.", bullet_style))
    story.append(Paragraph("• <b>Incubation Center:</b> GNDECB Innovation & Incubation Center fostering student entrepreneurship, idea prototyping, seed funding guidance, and intellectual property/patent registration.", bullet_style))
    story.append(Paragraph("• <b>Student Corner:</b> Hub for student co-curricular activities, technical clubs, cultural events, sports meets, and national/state scholarship facilitation (SSP, NSP, Vidyasiri).", bullet_style))
    story.append(Paragraph("• <b>Maintenance Cell:</b> Comprehensive campus upkeep division ensuring 24/7 power backup, clean water filtration, laboratory hardware maintenance, and green campus management.", bullet_style))
    story.append(Paragraph("• <b>Medical Facility:</b> On-campus Health Center with qualified medical personnel, emergency first aid, routine health checks, pharmacy, and tie-ups with multi-specialty hospitals with ambulance service.", bullet_style))
    story.append(Paragraph("• <b>Youth Red Cross (YRC):</b> Active volunteer wing promoting humanitarian services, voluntary blood donation drives, disaster relief readiness, and health awareness.", bullet_style))
    story.append(Paragraph("• <b>NPTEL Local Chapter:</b> Official SWAYAM NPTEL local chapter offering MOOC certifications, credit transfers, technical self-learning courses, and exam center coordination.", bullet_style))
    story.append(Paragraph("• <b>Hostel (Boys & Girls):</b> Secure residential hostels with Wi-Fi, hygienic North and South Indian dining mess, indoor gymnasium, reading rooms, and round-the-clock security surveillance.", bullet_style))
    story.append(Paragraph("• <b>CAMU Digital ERP Portal:</b> Integrated cloud-based college ERP for students and parents to track real-time attendance, internal assessment marks, fee receipts, timetables, and academic notifications.", bullet_style))
    story.append(Paragraph("• <b>Online Grievance Redressal Form:</b> Dedicated online portal and Internal Complaints Committee (ICC) / Anti-Ragging Cell for transparent, confidential resolution of student grievances.", bullet_style))
    
    story.append(Spacer(1, 4))
    
    # ---------------- PAGE 2 CONTINUED: RESEARCH & DEVELOPMENT -------------
    story.append(Paragraph("4. Research & Development (R&D) Cell Highlights", h2_style))
    story.append(Paragraph(
        "• <b>Accreditation:</b> NAAC A+ Grade Institution | Approved by AICTE & VTU Affiliated.<br/>"
        "• <b>Research Centers:</b> <b>8 VTU Recognized Research Centers</b> across engineering disciplines and sciences.<br/>"
        "• <b>Faculty Strength:</b> <b>34 Doctorate (Ph.D.) Faculty Members</b> and <b>23 Recognized Research Supervisors</b>.<br/>"
        "• <b>Scholars:</b> <b>58 Registered Research Scholars</b> pursuing Ph.D. under university guides.<br/>"
        "• <b>Collaborations & MoUs:</b> <b>15+ National & Global MoUs</b> with premier industries and academia.<br/>"
        "• <b>IPR Cell:</b> Intellectual Property Rights & Patent Facilitation Cell supporting student innovations and patent filings.",
        body_style
    ))
    
    story.append(Spacer(1, 4))
    
    # Contact Details
    story.append(Paragraph("5. College Contact Information & Address", h2_style))
    story.append(Paragraph(
        "<b>Address:</b> Guru Nanak Dev Engineering College, Mailoor Road, Bidar, Karnataka - 585403, India.<br/>"
        "<b>Telephone:</b> 08482-226949 / 08482-235214 / +91-9741892834 | <b>Email:</b> principal@gndecb.ac.in | <b>Website:</b> https://gndecb.ac.in",
        body_style
    ))
    
    doc.build(story)
    print(f"Generated {pdf_path}")

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    create_tp_brochure()
    create_college_brochure()

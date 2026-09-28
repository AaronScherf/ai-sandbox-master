#set page(paper: "us-letter", margin: (top: 0.4in, right: 0.5in, bottom: 0.5in, left: 0.5in))
#set text(size: 9.5pt, fill: rgb("#333333"))
#set heading(numbering: none)
#set list(spacing: 0.28em)
#show heading.where(level: 1): it => align(center, block(below: 0.4em)[
  #text(size: 18pt, fill: rgb("#111111"), upper(it.body))
])
#show heading.where(level: 2): it => block(above: 0.7em, below: 0.5em)[
  #text(size: 11pt, fill: rgb("#003366"), tracking: 0.5pt, upper(it.body))
  #line(length: 100%, stroke: 0.5pt + rgb("#cccccc"))
]
#show heading.where(level: 3): it => block(above: 0.6em, below: 0.2em)[
  #text(size: 10pt, weight: "bold", it.body)
]
#let job-heading(org, role, dates) = block(above: 0.6em, below: 0.2em)[
  #if dates == none [
    #text(size: 10pt, weight: "bold", org)
  ] else [
    #grid(columns: (1fr, auto), column-gutter: 1em, align: (left, right),
      text(size: 10pt, weight: "bold", org),
      text(size: 10pt, weight: "bold", dates),
    )
  ]
  #text(size: 10pt, style: "italic", role)
]

= Aaron Scherf

#align(center)[theaaronscherf\@gmail.com • https://www.linkedin.com/in/aaron-scherf/ • https://aaronscherf.github.io/]

== Work Experience

#job-heading([U.S. Agency for International Development], [Foreign Service Officer - Monitoring, Evaluation, Learning Team Lead (FS 3-5)], [03/2024 – 07/2025])

Kyiv, Ukraine

- Managed inventory and asset databases for electrical infrastructure and humanitarian equipment across 16+ projects, supporting analytics system tracking \$5Bn in infrastructure support.
- Developed analytics system to track \$5Bn in electrical infrastructure support by administrative geography.
- Supervised implementation of 20 program evaluations, including leading design of a \$1.5M randomized control trial to evaluate impact of \$450M credit facilitation program for small businesses.
- Supervised \$36M contract for monitoring, evaluation, and learning services, developing new systems for performance tracking, strategy alignment, and context research.
- Co-created third-party monitoring system which conducted over 3,000 verification visits in a year.
- Led collection of annual performance metrics and sectoral narratives for 52 development programs, aligning inter-agency indicator framework with new countrywide strategy and scorecard.

#job-heading([U.S. Agency for International Development], [Foreign Service Officer - Gender Equity and Program Design Officer (FS 4-9)], [02/2022 – 03/2024])

Bogota, Colombia

- Led design and context research for four programs in smallholder agriculture, environmental conservation, and rural land titling.
- Led the design process for four new programs in smallholder agriculture, environmental conservation, and rural land titling, developing indicators to measure job-expanding policy reforms.
- Developed data system to process and classify high-resolution drone imagery, resulting in over 600 new land titles issued to smallholder farmers.
- Supported 32 programs to re-align performance indicators with gender equity and social inclusion principles, including multiple presentations to contract partner teams in Spanish.

#job-heading([U.S. Agency for International Development], [Foreign Service Officer - Program Officer Rotations (FS 5-12)], [07/2020 – 02/2022])

Washington, DC, USA

- Developed new budget data processing and visualization tool using Python and Tableau, saving hundreds of hours of staff time.
- Led team of 15 staff as acting Office Director and Budget Lead for 3 months during \$1.7Bn congressional funding negotiations and supervised over \$60M in realignment of program funds.
- Mentored 220 staff on applications of artificial intelligence and data analytics platforms to improve program delivery and performance reporting.
- Led knowledge management pilot program with South Sudan office, designing staff transition resources and implementation plan for improving handovers and file management in Juba.

#block(breakable: false)[
== Education

=== Columbia University

- PhD in Sustainable Development
- New York, NY, USA • 08/2026 – Present

=== Georgia Institute of Technology

- Master of Science in Computer Science • GPA: 3.88
- Atlanta, GA, USA • 01/2022 – 12/2025

=== Indiana State University

- Master of Science in Mathematics • GPA: 3.85
- Terre Haute, IN, USA • 05/2021 – 05/2024
- Thesis: Novel Omnibus Normality Test and Power Comparison with the Shapiro-Wilk

=== University of California, Berkeley

- Master of Science in Development Practice • GPA: 3.94
- Berkeley, CA, USA • 07/2018 – 05/2020
- Thesis: Predicting the Yield of CIMMYT Wheat Genotypes via Remote Sensing and Machine Learning

=== Heidelberg University

- Master of Science (audited) in Economics
- Heidelberg, DE • 07/2017 – 06/2018

=== Mercer University

- Bachelor in Finance and Economics • GPA: 3.91
- Macon, GA, USA • 08/2013 – 05/2017
- Thesis: Analyzing Regional Economic Impacts of Syrian Refugee Crisis in Turkey
]

#block(breakable: false)[
== Awards & Scholarships

- Donald M. Payne Fellow (05/2017) — \$100,000 fellowship with USAID
- Fulbright Scholar (05/2017) — Research Fellow at ZEW / Heidelberg, DE
- Humanity in Action Senior Fellow (05/2017) — in partnership with Amnesty International
- Stamps Foundation Leadership Scholar (05/2013) — \$240,000 merit scholarship
- Payne International Development Fellow (Not specified) — \$90,000 Graduate Fellowship with USAID
- Fulbright Graduate Research Award (Not specified) — \$10,000 Research Grant and Cultural Exchange Program
]

#block(breakable: false)[
== Research Presentations & Publications

- Applications of PCA for Mapping Regional Socioeconomic Vulnerability Indices (12/2019) — UC Berkeley: Data for Human Mobility Lab
- Integration Progress: Results from two Reallabor Surveys of Asylum Seekers (08/2018) — Centre for European Economic Research (ZEW) (#link("https://www.econstor.eu/handle/10419/231442")[link])
- Gentrification or Revitalization? Ethical Investment in Urban Property Development (04/2017) — National Conference on Undergraduate Research
- Economic Impact Assessment of Historic Property Rehabilitation in Macon, GA (04/2017) — Society of Business, Industry, and Economics Conference
- “OurBlock” - Blockchain Based Property Registry for South African Land Reform (03/2017) — Harvard Social Entrepreneurship Pitch Competition
- “How to Kill a Microfinance Fund” – Analysis of Microcredit Policy in South Africa (10/2016) — Southern Conference Undergraduate Research Forum
- “Bloomfield 2020” – Neighborhood Economic Development Plan (04/2016) — Clinton Global Initiative University at Berkeley, CA
- Autonomous Drone Deployment Grid for Improved Wildfire Response in California (05/2020) — UC Berkeley: Innovations in Disaster Response Showcase
- The End of Schengen? Reforms to the Dublin Regulation and EU Asylum Policy (08/2017) — Humanity in Action International Conference in Strasbourg, FR
]

#block(breakable: false)[
== Skills

*Computer Programming and Artificial Intelligence*: Python, R, JavaScript, Stata, MatLab, Excel, Machine Learning, Natural Language Processing, Artificial Neural Networks

*Applied Economic Research*: GIS Analysis (ArcGIS / GEE), Applied Econometrics, Mathematical Statistics, Labor Economic Research, Applied Mathematics, Development Economics

*Languages and Other*: Spanish - Professional, German - Intermediate, Program Evaluation, Empirical Policy Analysis, Information Communications Technology

*Computer Programming*: Python, R, JavaScript

*Data Engineering*: SQL, Azure, GCP

*Agentic AI*: CrewAI, AutoGen

*Natural Language Processing*: 

*Data Visualization and Analysis*: Tableau, PowerBI

*Artificial Neural Networks*: Machine Learning, Large Language Models

*Cloud Architecture*: GCP, Azure

*RAG AI*: LangChain

*Google Earth Engine / GCP*: 

*Data Collection & Processing*: 
]
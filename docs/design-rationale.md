# Design rationale

This document explains the scientific and engineering reasoning behind lab.meteo@uniparthenope. Every cited work
is a peer-reviewed journal article or conference paper whose bibliographic record was verified
against its DOI.

## 1. Interactive notebooks as a research and teaching instrument

Computational notebooks interleave narrative, code, and results, and have become a primary medium
for exploratory analysis and for communicating computational work. Kluyver et al. [1] framed the
Jupyter notebook as a publishing format for reproducible workflows, and Granger and Pérez [2]
describe it as a tool for "thinking and storytelling with code and data". The same flexibility,
however, threatens reproducibility: in a study of 1.4 million public notebooks, Pimentel et al. [3]
could re-execute only a minority with identical results, mostly because of undeclared dependencies
and out-of-order execution. Rule et al. [4] condensed community practice into rules that lab.meteo@uniparthenope
operationalises: pinned environments, parameterised headless execution (Papermill), notebooks kept
without transient output, and data provenance stated in each notebook.

Multi-user notebook services are an established pattern in research computing. Zonca and Sinkovits
[5] showed how JupyterHub with container spawners serves workshops and science gateways at scale;
lab.meteo@uniparthenope follows that pattern on a single host, with one container per user and a persistent volume
per workspace. Containers make the analysis environment itself an inspectable, versioned artefact
[6], which is why both images pin their base by digest and their direct Python dependencies by
version.

## 2. A Colab-style, two-tier user experience

The interaction model follows the widely adopted hosted-notebook pattern: an anonymous visitor
lands on a gallery, opens a notebook with one click, and runs it without installing anything, while
a signed-in member "connects" to a persistent server runtime. lab.meteo@uniparthenope implements the anonymous tier
with JupyterLite, whose Python kernel is Pyodide compiled to WebAssembly. WebAssembly was designed
as a safe, portable, near-native execution target for the browser sandbox [7]; running anonymous
code client-side therefore removes the most significant risk of public notebook services —
arbitrary code execution on institutional servers — while keeping the editing experience intact.
The signed-in tier provides what the browser cannot: the full scientific stack (Xarray [8], Dask,
Zarr, Cartopy), persistent storage, and direct read access to the operational archives.

Google Colaboratory made this pattern familiar to a generation of students and researchers by
combining zero-installation access, free compute, and a single-document editor, at the price of
proprietary infrastructure and time-limited sessions [23]. lab.meteo@uniparthenope keeps the
familiar gestures — an *Open notebook* dialog with examples, recent files, GitHub, and upload; the
`/github/<owner>/<repo>/blob/<ref>/<path>` URL scheme; *Connect*, *Restart runtime*, and
*Disconnect and delete runtime*; Colab's keyboard shortcuts — but implements them on open-source
Jupyter components and University infrastructure, so that data stays under institutional control
and the operational archives are reachable without copying. Studies of notebook practice show that
notebooks serve both exploration and explanation, and that the two goals pull in different
directions [24]; that notebooks are widely used as vehicles of open science [25]; and that only a
minority of published notebooks re-execute with the same results [3]. Opening a notebook from its
public repository into a runtime with a fixed, versioned scientific stack and the original data
therefore lowers the cost of re-execution, which is the first step towards reproducibility.

Visual identity mirrors the public meteo@uniparthenope forecast site and sensor-network portal
(gradient navigation, circular logo, card layout, day/night themes) so that the workspace is
perceived as part of the same institutional service.

## 3. Data: operational archives exposed read-only

The meteo@uniparthenope operational chain produces atmospheric (WRF [9]), ocean (ROMS [10]), wave
(WaveWatch III), water-quality (WaComM [11]), and AI-based aquaculture (AIquam) products, and the
centre operates a coastal weather-station network. Earlier work of the group on workflow-driven
processing of environmental data [12], [13] motivates exposing these archives to analysts directly
rather than through copies: copies drift, consume storage, and break provenance.

Exposing a production archive to arbitrary user code requires that the archive cannot be altered.
lab.meteo@uniparthenope enforces this at three independent layers, following the principle of least privilege and
defence in depth [14]: (i) every shared path is bind-mounted read-only by the container engine;
(ii) user containers run with all Linux capabilities dropped and `no-new-privileges`, so a process
cannot remount a filesystem read-write; and (iii) the Hub refuses to spawn a server whose mount
plan contains a writable shared path. File ownership on the host provides a fourth, incidental
barrier. Container isolation has known limits [15]; the residual risk concentrates in the Hub's
access to the Docker socket, which is documented in [Security](security.md).

The layout of the archives (`mmm/ddd/archive|history/YYYY/MM/DD/…`) is preserved unchanged inside
user servers so that notebooks written in lab.meteo@uniparthenope run unmodified on the centre's processing hosts,
supporting the reusability goals of the FAIR principles [16].

## 4. Identity, roles, and administration

Role-based access control assigns permissions to roles rather than individuals, which simplifies
review and revocation [17]. lab.meteo@uniparthenope maps four platform roles onto JupyterHub's RBAC scopes and
groups: *student* (small resource tier), *user*, *instructor* (read-only oversight of users and
start/stop of student servers), *researcher* (large tier), plus the built-in *administrator*.
Roles also select per-user resource limits, so that teaching cohorts cannot exhaust capacity
needed by research workloads.

Universities already operate identity providers. Federated identity management lets a service
rely on the institution's authentication instead of storing passwords [18]. lab.meteo@uniparthenope therefore
supports Microsoft Entra ID (university Microsoft 365 tenants) and Google Workspace for Education
through OAuth 2.0/OpenID Connect, restricted to the institution's tenant or hosted domains; local
accounts with administrator approval remain available for pilots and external collaborators.

The platform dashboard gathers what an administrator needs to discharge accountability duties:
accounts and roles, a live audit proving that no user container holds a writable shared mount,
archive freshness, data-subject requests, orphaned workspaces, and the security posture
(HTTPS, sign-up policy, idle culling).

## 5. Data protection by design

The GDPR requires data protection by design and by default (Art. 25) and accountability (Art. 5(2))
[19]. Spiekermann [20] argues that privacy by design succeeds only when translated into concrete
engineering decisions; lab.meteo@uniparthenope's are:

- **Minimisation:** no e-mail at sign-up, no analytics, no third-party resources on Hub pages, and
  only strictly necessary cookies (hence no consent banner is required).
- **Storage limitation:** idle servers are culled; inactive accounts are reviewed after a
  configurable period; erasure removes the account and its workspace volume.
- **Transparency and rights:** a layered privacy notice; self-service access and portability
  (machine-readable JSON export); a request register for erasure, rectification, and restriction
  with administrator workflow and audit log.
- **Security of processing (Art. 32):** container hardening, strict security headers, approval-gated
  accounts, failed-login throttling, and HTTPS readiness.
- **Anonymous tier:** notebook content never leaves the browser; the notice discloses the content
  delivery network that serves the Pyodide runtime.

## 6. Accessibility

Public-sector websites in the EU must conform to EN 301 549, which incorporates WCAG 2.1 level AA;
in Italy this obligation is implemented by Law 4/2004 and the AgID guidelines. Empirical reviews
show that educational websites frequently fail basic success criteria such as contrast, labels, and
keyboard operation [21], and data-science notebooks are particularly problematic for screen-reader
users [22]. lab.meteo@uniparthenope addresses what it controls — Hub pages, gallery, sign-in, and administration —
with semantic landmarks, a skip link, labelled forms, AA contrast in both themes, visible focus,
text-not-colour status indicators, and reduced-motion support, and publishes an accessibility
statement listing the residual limitations of JupyterLab-based content.

## References

1. T. Kluyver, B. Ragan-Kelley, F. Pérez, B. Granger, et al., “Jupyter Notebooks – a publishing
   format for reproducible computational workflows,” in *Positioning and Power in Academic
   Publishing: Players, Agents and Agendas* (ELPUB 2016), IOS Press, 2016, pp. 87–90.
   doi:[10.3233/978-1-61499-649-1-87](https://doi.org/10.3233/978-1-61499-649-1-87)
2. B. E. Granger and F. Pérez, “Jupyter: Thinking and storytelling with code and data,”
   *Computing in Science & Engineering*, vol. 23, no. 2, pp. 7–14, 2021.
   doi:[10.1109/MCSE.2021.3059263](https://doi.org/10.1109/MCSE.2021.3059263)
3. J. F. Pimentel, L. Murta, V. Braganholo, and J. Freire, “A large-scale study about quality and
   reproducibility of Jupyter notebooks,” in *Proc. IEEE/ACM 16th Int. Conf. on Mining Software
   Repositories (MSR)*, 2019, pp. 507–517.
   doi:[10.1109/MSR.2019.00077](https://doi.org/10.1109/MSR.2019.00077)
4. A. Rule, A. Birmingham, C. Zuniga, I. Altintas, et al., “Ten simple rules for writing and
   sharing computational analyses in Jupyter Notebooks,” *PLOS Computational Biology*, vol. 15,
   no. 7, e1007007, 2019. doi:[10.1371/journal.pcbi.1007007](https://doi.org/10.1371/journal.pcbi.1007007)
5. A. Zonca and R. S. Sinkovits, “Deploying Jupyter Notebooks at scale on XSEDE resources for
   science gateways and workshops,” in *Proc. Practice and Experience on Advanced Research
   Computing (PEARC ’18)*, ACM, 2018, pp. 1–7.
   doi:[10.1145/3219104.3219122](https://doi.org/10.1145/3219104.3219122)
6. C. Boettiger, “An introduction to Docker for reproducible research,” *ACM SIGOPS Operating
   Systems Review*, vol. 49, no. 1, pp. 71–79, 2015.
   doi:[10.1145/2723872.2723882](https://doi.org/10.1145/2723872.2723882)
7. A. Haas, A. Rossberg, D. L. Schuff, B. L. Titzer, et al., “Bringing the web up to speed with
   WebAssembly,” in *Proc. 38th ACM SIGPLAN Conf. on Programming Language Design and
   Implementation (PLDI)*, 2017, pp. 185–200.
   doi:[10.1145/3062341.3062363](https://doi.org/10.1145/3062341.3062363)
8. S. Hoyer and J. Hamman, “xarray: N-D labeled arrays and datasets in Python,” *Journal of Open
   Research Software*, vol. 5, no. 1, p. 10, 2017. doi:[10.5334/jors.148](https://doi.org/10.5334/jors.148)
9. J. G. Powers, J. B. Klemp, W. C. Skamarock, C. A. Davis, et al., “The Weather Research and
   Forecasting model: Overview, system efforts, and future directions,” *Bulletin of the American
   Meteorological Society*, vol. 98, no. 8, pp. 1717–1737, 2017.
   doi:[10.1175/BAMS-D-15-00308.1](https://doi.org/10.1175/BAMS-D-15-00308.1)
10. A. F. Shchepetkin and J. C. McWilliams, “The regional oceanic modeling system (ROMS): a
    split-explicit, free-surface, topography-following-coordinate oceanic model,” *Ocean
    Modelling*, vol. 9, no. 4, pp. 347–404, 2005.
    doi:[10.1016/j.ocemod.2004.08.002](https://doi.org/10.1016/j.ocemod.2004.08.002)
11. R. Montella, D. Di Luccio, P. Troiano, A. Riccio, A. Brizius, and I. Foster, “WaComM: A
    parallel water quality community model for pollutant transport and dispersion operational
    predictions,” in *Proc. 12th Int. Conf. on Signal-Image Technology & Internet-Based Systems
    (SITIS)*, IEEE, 2016, pp. 717–724. doi:[10.1109/SITIS.2016.120](https://doi.org/10.1109/SITIS.2016.120)
12. R. Montella, D. Di Luccio, L. Marcellino, A. Galletti, et al., “Workflow-based automatic
    processing for Internet of Floating Things crowdsourced data,” *Future Generation Computer
    Systems*, vol. 94, pp. 103–119, 2019.
    doi:[10.1016/j.future.2018.11.025](https://doi.org/10.1016/j.future.2018.11.025)
13. R. Montella, D. Di Luccio, S. Kosta, et al., “DagOn*: Executing direct acyclic graphs as
    parallel jobs on anything,” in *Proc. IEEE/ACM Workflows in Support of Large-Scale Science
    (WORKS)*, 2018, pp. 64–73. doi:[10.1109/WORKS.2018.00012](https://doi.org/10.1109/WORKS.2018.00012)
14. J. H. Saltzer and M. D. Schroeder, “The protection of information in computer systems,”
    *Proceedings of the IEEE*, vol. 63, no. 9, pp. 1278–1308, 1975.
    doi:[10.1109/PROC.1975.9939](https://doi.org/10.1109/PROC.1975.9939)
15. S. Sultan, I. Ahmad, and T. Dimitriou, “Container security: Issues, challenges, and the road
    ahead,” *IEEE Access*, vol. 7, pp. 52976–52996, 2019.
    doi:[10.1109/ACCESS.2019.2911732](https://doi.org/10.1109/ACCESS.2019.2911732)
16. M. D. Wilkinson, M. Dumontier, I. J. Aalbersberg, G. Appleton, et al., “The FAIR Guiding
    Principles for scientific data management and stewardship,” *Scientific Data*, vol. 3,
    160018, 2016. doi:[10.1038/sdata.2016.18](https://doi.org/10.1038/sdata.2016.18)
17. R. S. Sandhu, E. J. Coyne, H. L. Feinstein, and C. E. Youman, “Role-based access control
    models,” *Computer*, vol. 29, no. 2, pp. 38–47, 1996.
    doi:[10.1109/2.485845](https://doi.org/10.1109/2.485845)
18. S. S. Y. Shim, G. Bhalla, and V. Pendyala, “Federated identity management,” *Computer*,
    vol. 38, no. 12, pp. 120–122, 2005. doi:[10.1109/MC.2005.408](https://doi.org/10.1109/MC.2005.408)
19. C. J. Hoofnagle, B. van der Sloot, and F. Zuiderveen Borgesius, “The European Union general
    data protection regulation: what it is and what it means,” *Information & Communications
    Technology Law*, vol. 28, no. 1, pp. 65–98, 2019.
    doi:[10.1080/13600834.2019.1573501](https://doi.org/10.1080/13600834.2019.1573501)
20. S. Spiekermann, “The challenges of privacy by design,” *Communications of the ACM*, vol. 55,
    no. 7, pp. 38–40, 2012. doi:[10.1145/2209249.2209263](https://doi.org/10.1145/2209249.2209263)
21. M. Campoverde-Molina, S. Luján-Mora, and L. Valverde García, “Empirical studies on web
    accessibility of educational websites: A systematic literature review,” *IEEE Access*, vol. 8,
    pp. 91676–91700, 2020. doi:[10.1109/ACCESS.2020.2994288](https://doi.org/10.1109/ACCESS.2020.2994288)
22. V. Potluri, S. Singanamalla, N. Tieanklin, and J. Mankoff, “Notably inaccessible — Data driven
    understanding of data science notebook (in)accessibility,” in *Proc. 25th Int. ACM SIGACCESS
    Conf. on Computers and Accessibility (ASSETS ’23)*, 2023, pp. 1–19.
    doi:[10.1145/3597638.3608417](https://doi.org/10.1145/3597638.3608417)
23. T. Carneiro, R. V. Medeiros Da Nóbrega, T. Nepomuceno, G.-B. Bian, V. H. C. de Albuquerque,
    and P. P. Rebouças Filho, “Performance analysis of Google Colaboratory as a tool for
    accelerating deep learning applications,” *IEEE Access*, vol. 6, pp. 61677–61685, 2018.
    doi:[10.1109/ACCESS.2018.2874767](https://doi.org/10.1109/ACCESS.2018.2874767)
24. A. Rule, A. Tabard, and J. D. Hollan, “Exploration and explanation in computational notebooks,”
    in *Proc. 2018 CHI Conference on Human Factors in Computing Systems*, ACM, 2018, pp. 1–12.
    doi:[10.1145/3173574.3173606](https://doi.org/10.1145/3173574.3173606)
25. B. M. Randles, I. V. Pasquetto, M. S. Golshan, and C. L. Borgman, “Using the Jupyter notebook as
    a tool for open science: An empirical study,” in *Proc. 2017 ACM/IEEE Joint Conference on
    Digital Libraries (JCDL)*, IEEE, 2017, pp. 1–2.
    doi:[10.1109/JCDL.2017.7991618](https://doi.org/10.1109/JCDL.2017.7991618)

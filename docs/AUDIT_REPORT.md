DocuMentor Project
Complete Security Audit
Report
Comprehensive Analysis of Code Quality, Security, and
Architecture
GitHub Repository: Asphyksia/DocuMentor
https://github.com/Asphyksia/DocuMentor
Audit Date: March 26, 2026
Prepared by: Z.ai Security Audit Team
1. Executive Summary
DocuMentor is an open-source intelligent document analysis platform designed for universities, combining
document parsing, RAG-powered search, and LLM inference into a unified web interface with interactive
dashboards. The project orchestrates multiple existing open-source tools including SurfSense for RAG
operations, Docling for document parsing, and Hermes Agent for AI reasoning capabilities. This audit
provides a comprehensive evaluation of the project's security posture, code quality, architecture design, and
overall readiness for deployment in academic environments.
The audit reveals that DocuMentor is a well-structured project with thoughtful architectural decisions, but it
carries several security considerations that must be addressed before production deployment. The project
demonstrates competent use of modern technologies including FastAPI, Next.js 14, and Docker
containerization. However, the lack of authentication, the permissive CORS configuration, and the exposure
of API keys through environment variables represent significant security concerns that require immediate
attention.
Category Score Status
Architecture Design 8/10 Good
Code Quality 7/10 Satisfactory
Security Posture 5/10 Needs Improvement
Documentation 8/10 Good
Dependency Management 7/10 Satisfactory
Production Readiness 4/10 Not Ready
Table 1. Audit Summary Scores
2. Project Overview
DocuMentor is positioned as a self-hosted document intelligence platform specifically designed for
universities. The system enables users to upload various document formats including PDF, Excel, Word, and
PowerPoint files, then query the content using natural language through an integrated chat interface. The
platform renders extracted data as interactive charts including bar graphs, line charts, area charts, pie charts,
and KPI indicators. The optional Hermes Agent integration provides intelligent query routing with
multi-step tool use capabilities, significantly enhancing the quality of responses compared to basic search
operations.
2.1 Technology Stack
The project employs a modern technology stack comprising FastAPI and WebSocket for the backend bridge
server, Next.js 14 with React 18 for the frontend dashboard, PostgreSQL 17 with pgvector extension for
vector storage, Redis with Celery for task queuing, and Docker Compose for container orchestration. The
document parsing leverages IBM's Docling library running locally within Docker containers, while
embeddings are generated using the sentence-transformers/all-MiniLM-L6-v2 model. The LLM inference is
designed to work with any OpenAI-compatible provider, with RelayGPU recommended as the default
option.
2.2 Architecture Overview
The system architecture follows a layered design pattern with clear separation of concerns. The frontend
layer consists of a Next.js dashboard running on port 3000, communicating with a WebSocket bridge server
on port 8001. The bridge server acts as an intelligent gateway, routing queries through Hermes Agent for
reasoning when available, or directly to the MCP wrapper for CRUD operations. The MCP wrapper exposes
25 SurfSense tools via both Streamable HTTP and JSON-RPC protocols, interacting with the SurfSense
backend on port 8929. The SurfSense backend integrates with PostgreSQL for persistence, Redis for caching
and queuing, and Celery workers for asynchronous document processing tasks.
3. Security Analysis
The security analysis of DocuMentor reveals several areas of concern that must be addressed before the
system can be considered production-ready. While the project demonstrates good practices in some areas
such as input validation and filename sanitization, other aspects require significant improvement to meet
enterprise security standards.
3.1 Critical Security Issues
Issue Severity Description
No Authentication System CRITICAL
The application lacks any user authentication
mechanism. All endpoints are openly accessible,
exposing sensitive document data to unauthorized
access.
Permissive CORS Configuration HIGH
The bridge server uses allow_origins=["*"],
permitting requests from any domain. This creates
cross-site request forgery vulnerabilities.
API Key Exposure Risk HIGH
API keys are stored in .env files and passed to
frontend via environment variables. Keys could
leak through logs, error messages, or client-side
exposure.
No Rate Limiting MEDIUM
The WebSocket bridge and MCP wrapper lack rate
limiting, making them vulnerable to
denial-of-service attacks and resource exhaustion.
Unencrypted WebSocket MEDIUM
WebSocket connections use ws:// protocol without
TLS encryption, exposing transmitted data to
interception.
Table 2. Critical Security Issues Identified
3.2 Authentication and Authorization
The project explicitly acknowledges its single-user design limitation in the documentation, stating that no
authentication, RBAC, or multi-tenancy features are implemented. SurfSense uses a single admin account
configured through environment variables, which is acceptable for personal or development use but entirely
unsuitable for production deployment in university environments where multiple users with different access
levels must be supported. The absence of session management, password policies, and audit logging for user
actions represents a significant compliance risk for institutions subject to data protection regulations.
3.3 Input Validation and Sanitization
The project demonstrates competent input validation practices. The bridge server uses Pydantic models to
validate all incoming WebSocket messages, with explicit field validators including minimum and maximum
length constraints, type checking, and custom validators for filename sanitization. The UploadPayload class
includes a sanitize_filename validator that strips path traversal attempts using Path(v).name, preventing
directory traversal attacks. File uploads are limited to 50MB with validation performed before processing,
and base64 data is decoded with validation enabled to prevent malformed input. The message dispatcher
uses an explicit allowlist of handlers rather than generic passthrough, reducing the attack surface for
message-type injection.
3.4 Data Protection
Document processing runs locally via Docling within Docker containers, and embeddings are generated
using the local sentence-transformers model, meaning no document content leaves the host machine during
parsing and indexing phases. However, LLM queries transmit document text to external providers, which
the documentation acknowledges. For complete data locality, users would need to configure a local model
through Ollama. The project correctly states that no telemetry data is collected. Temporary files created
during uploads are cleaned up after processing, though the cleanup uses a simple try/except block that may
fail silently in edge cases. The JWT tokens used for SurfSense authentication are cached with a 55-minute
TTL and automatically refreshed on 401 responses, representing a reasonable session management approach
for the backend communication.
3.5 Security Recommendations
• Implement OAuth 2.0 or similar authentication system with support for university SSO integration
• Replace allow_origins=['*'] with explicit domain whitelisting in CORS configuration
• Add rate limiting to WebSocket connections and API endpoints using tools like slowapi or custom
middleware
• Implement TLS encryption for all WebSocket connections using wss:// protocol
• Store API keys in secure secret management systems (HashiCorp Vault, AWS Secrets Manager) instead of
.env files
• Add comprehensive audit logging for all document operations and user actions
• Implement input sanitization for LLM prompts to prevent prompt injection attacks
4. Code Quality Analysis
The codebase demonstrates a professional approach to software development with consistent styling,
appropriate use of modern Python and TypeScript features, and clear architectural separation. However,
several areas could benefit from additional attention to improve maintainability and reduce technical debt.
4.1 Backend Code Quality
The Python backend code follows clean code principles with comprehensive docstrings, type hints, and
logical function organization. The bridge.py file (877 lines) and mcp_wrapper.py (716 lines) are
well-structured with clear section separators and consistent naming conventions. Error handling is thorough
with custom error codes and structured error responses. The use of Pydantic models for validation provides
both runtime safety and documentation benefits. The ThreadPoolExecutor pattern used for running the
synchronous AIAgent in an async context is appropriately implemented with a maximum of 4 workers and
proper callback cleanup.
Areas for improvement include the singleton pattern used for the AIAgent instance, which creates a query
lock that serializes requests and limits concurrency. The conversation history dictionary indexed by
WebSocket ID could grow unbounded if connections are not properly cleaned up. Error handling in some
places catches broad Exception types rather than specific exceptions, potentially masking unexpected
failures. The logging configuration uses basic stdout output without rotation or structured logging, which
would be beneficial for production debugging.
4.2 Frontend Code Quality
The Next.js frontend demonstrates modern React patterns with custom hooks for state management, proper
separation of concerns between components, and consistent use of TypeScript types. The useBridge hook
implements a robust WebSocket connection with automatic reconnection and proper cleanup on unmount.
The ChatPanel component effectively uses Framer Motion for animations and maintains responsive design
principles. The discriminated union types for WebSocket messages provide type safety across the bridge
communication layer.
The frontend lacks comprehensive error boundary handling, meaning unexpected errors could crash the
entire application without user-friendly feedback. The useEffect dependency arrays in page.tsx are disabled
with eslint-disable comments, potentially masking dependency-related bugs. The WebSocket reconnection
logic uses a fixed delay of 3 seconds without exponential backoff, which could create thundering herd
scenarios during server restarts. Component styling is managed through inline Tailwind classes, which
works well for this project size but may become unwieldy as the codebase grows.
Metric Backend Frontend
Lines of Code ~1,600 (Python) ~1,200 (TypeScript)
Type Coverage High (type hints) High (TypeScript)
Documentation Good (docstrings) Limited (comments)
Error Handling Good Needs Improvement
Test Coverage None visible None visible
Table 3. Code Quality Metrics Summary
5. Dependency Analysis
The project manages dependencies through requirements.txt for Python and package.json for Node.js. While
the dependency footprint is relatively small, several considerations merit attention for production
deployment.
5.1 Backend Dependencies
The Python dependencies are minimal and well-chosen: FastAPI for the web framework, uvicorn as the
ASGI server, httpx for async HTTP client operations, Pydantic for data validation, python-multipart for file
uploads, python-dotenv for environment configuration, websockets for WebSocket support, and mcp[cli] for
Model Context Protocol implementation. Notably, all dependencies use version constraints with >=
operators rather than pinning exact versions, which ensures compatibility with security patches but could
introduce breaking changes in minor versions. The absence of dependency vulnerability scanning tools like
safety or pip-audit from the development workflow represents a gap in the security posture.
5.2 Frontend Dependencies
The Node.js dependencies include Next.js 14, React 18, Recharts for data visualization, Lucide React for
icons, Framer Motion for animations, and several Radix UI primitives for accessible component patterns.
The devDependencies include TypeScript, Tailwind CSS, ESLint, and their respective configurations.
Similar to the backend, versions use caret (^) constraints rather than exact pins. The absence of a
package-lock.json file in the repository could lead to inconsistent dependency resolution across different
environments. Running npm audit would be advisable to check for known vulnerabilities in the dependency
tree.
5.3 Docker and Infrastructure
The Docker setup uses python:3.11-slim as the base image, which is appropriate for size and security. The
Dockerfiles are minimal, installing curl for health checks and copying only necessary files. The
docker-compose.yml orchestrates services with proper dependency chains, health checks, and restart
policies. However, the containers run as root by default, and no security hardening measures such as
read-only filesystems or capability dropping are implemented. The inclusion of SurfSense as a submodule
means the security of the overall system also depends on the security posture of the SurfSense project.
6. Documentation Review
The project documentation is comprehensive and well-organized, representing one of the stronger aspects of
the codebase. The README.md provides clear installation instructions, environment variable
documentation, troubleshooting guidance, and architectural overviews. The ARCHITECTURE.md
document offers detailed technical explanations of data flow, component responsibilities, and known
limitations. The DOCSTEMPLATES.md defines JSON schemas for dashboard visualizations. The
HERMES_INTEGRATION_PLAN.md outlines the phased approach to agent integration, and the
CONTRIBUTING.md establishes contribution guidelines. The inline code documentation through
docstrings is thorough for the backend, though frontend comments are sparse.
Documentation gaps include the absence of API reference documentation for the MCP tools, lack of
developer setup instructions for running tests, missing deployment guides for production environments, and
no runbook for operational procedures. The troubleshooting section could be expanded with more common
error scenarios and their resolutions. Additionally, security considerations are mentioned but not elaborated
upon in a dedicated security documentation section.
7. Recommendations
7.1 Immediate Actions (Critical Priority)
• Implement authentication and authorization system before any production deployment
• Restrict CORS configuration to explicit whitelisted domains
• Add rate limiting to prevent abuse and denial-of-service attacks
• Enable TLS encryption for all network communications including WebSocket
7.2 Short-term Improvements (High Priority)
• Add comprehensive unit and integration test coverage
• Implement structured logging with log rotation and centralized collection
• Create API documentation using OpenAPI/Swagger for the MCP tools
• Add dependency vulnerability scanning to CI/CD pipeline
• Implement proper secret management for API keys and credentials
7.3 Long-term Enhancements (Medium Priority)
• Implement multi-tenancy support for university deployment scenarios
• Add audit logging and compliance reporting features
• Create deployment guides for various cloud providers
• Implement agent pool pattern to enable concurrent query processing
• Add monitoring and alerting integration with tools like Prometheus and Grafana
8. Conclusion
DocuMentor represents a thoughtfully designed document intelligence platform with a solid technical
foundation. The project demonstrates competent use of modern technologies, clear architectural separation,
and comprehensive documentation. The integration of SurfSense for RAG operations, Hermes Agent for
intelligent query routing, and the MCP wrapper for tool abstraction shows good understanding of the AI
tooling ecosystem.
However, the project is explicitly not production-ready, as acknowledged in its own documentation. The
absence of authentication, permissive CORS configuration, and lack of rate limiting represent significant
security vulnerabilities that must be addressed before any deployment beyond personal development
environments. Organizations considering DocuMentor should implement a comprehensive security
hardening phase before deployment, including the addition of enterprise authentication, encrypted
communications, and proper audit logging.
For academic environments where data privacy and multi-user access are requirements, substantial
additional development will be necessary. The project's MIT license permits modification and redistribution,
allowing institutions to fork and enhance the security posture according to their specific requirements. With
appropriate security investments, DocuMentor could serve as an excellent foundation for university
document intelligence initiatives.

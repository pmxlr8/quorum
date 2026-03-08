from backend.services.orchestrator import orchestrator


def test_route_finance_question() -> None:
    agent, role = orchestrator.route('What is the budget and runway impact?')
    assert agent == 'sarah_kim'
    assert role == 'CFO'


def test_route_legal_question() -> None:
    agent, role = orchestrator.route('Any legal compliance and liability concerns?')
    assert agent == 'marcus_webb'
    assert role == 'Legal'


def test_route_tech_question() -> None:
    agent, role = orchestrator.route('What are the architecture and latency risks?')
    assert agent == 'alex_chen'
    assert role == 'CTO'

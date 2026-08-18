import sys

def rewrite_writer():
    with open('apps/api/pipeline/ingestion/writer.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # First, insert run_query at the top
    run_query_def = """
def run_query(hydra: HydraDB, query: str, **kwargs):
    with hydra._driver.session() as db_session:
        db_session.run(query, **kwargs)

def write_to_hydradb(
"""
    content = content.replace("def write_to_hydradb(\n", run_query_def)

    # Next, remove the transaction and with blocks, unindenting their contents
    # This is a bit tricky with raw text, so let's just do targeted replacements.
    lines = content.split('\n')
    new_lines = []
    
    in_with = False
    in_transaction = False
    
    for i, line in enumerate(lines):
        if "with hydra._driver.session() as db_session:" in line and "def write_to_hydradb" not in content[:content.find(line)]:
            # This is the main block
            continue
            
        if "with db_session.begin_transaction() as transaction:" in line:
            # We skip this line
            continue
            
        if "db_session.run(" in line:
            line = line.replace("db_session.run(", "run_query(hydra, ")
        
        if "transaction.run(" in line:
            line = line.replace("transaction.run(", "run_query(hydra, ")
            
        # We need to unindent lines that were inside the 'with' or 'transaction' blocks
        if line.startswith("    ") and not line.startswith("        ") and "def " not in line and "return " not in line and "return {" not in line and "    \"" not in line and "    }" not in line:
            pass # Keep it, these are top level inside write_to_hydradb
            
        # Actually it's easier to just replace the calls and not worry about indentation for Python parsing as long as it's consistent.
        # But Python cares about indentation.
        # A simple string replace of 'db_session.run' with 'run_query(hydra' and keeping the 'with' block is valid Python!
        new_lines.append(line)
        
    # Wait, if we keep the 'with hydra._driver.session() as db_session:' block but replace 'db_session.run' with 'run_query', we are STILL opening an outer session that isn't used! That's fine!
    pass

def simple_rewrite():
    with open('apps/api/pipeline/ingestion/writer.py', 'r', encoding='utf-8') as f:
        content = f.read()

    run_query_def = """
def run_query(hydra: HydraDB, query: str, **kwargs):
    with hydra._driver.session() as db_session:
        db_session.run(query, **kwargs)

def write_to_hydradb(
"""
    content = content.replace("def write_to_hydradb(\n", run_query_def)

    # Replace all .run calls
    content = content.replace("db_session.run(", "run_query(hydra, ")
    content = content.replace("transaction.run(", "run_query(hydra, ")
    
    # Replace MATCH + CREATE with MERGE in all places where it happens
    content = content.replace("MATCH (s:Session {id: $session_int_id}) CREATE (s)-[:CONTAINS]->(m:Message {id: $msg_int_id})",
                              "MERGE (s:Session {id: $session_int_id})-[:CONTAINS]->(m:Message {id: $msg_int_id})")
    content = content.replace("MATCH (s:Session {id: $session_int_id}) CREATE (s)-[:HAS_SUMMARY]->(sum:Summary {id: $summary_int_id})",
                              "MERGE (s:Session {id: $session_int_id})-[:HAS_SUMMARY]->(sum:Summary {id: $summary_int_id})")
    content = content.replace("MATCH (f:Fact {id: $fact_int_id}) CREATE (f)-[:OCCURRED_IN]->(s:Session {id: $session_int_id})",
                              "MERGE (f:Fact {id: $fact_int_id})-[:OCCURRED_IN]->(s:Session {id: $session_int_id})")

    # Replace MATCH + CREATE for supersedes and invalidates
    content = content.replace("CREATE (f_new)-[:SUPERSEDES]->(f_old)", "MERGE (f_new)-[:SUPERSEDES]->(f_old)")
    content = content.replace("CREATE (f)-[:INVALIDATED_BY {reason: $reason}]->(s)", "MERGE (f)-[:INVALIDATED_BY {reason: $reason}]->(s)")
    
    with open('apps/api/pipeline/ingestion/writer.py', 'w', encoding='utf-8') as f:
        f.write(content)

simple_rewrite()

#!/usr/bin/env python3
"""Debug script for export query issue"""

from sqlalchemy import create_engine, select, and_
from sqlalchemy.orm import Session, aliased
from app.database.config import get_prelude_db, prelude_engine
from app.models.prelude import Alert, DetectTime, CreateTime, Classification, Impact, Address, Analyzer, Node

def test_export_query():
    """Test the export query directly"""
    
    with Session(prelude_engine) as db:
        # Build the query exactly as in export.py
        source_addr = aliased(Address)
        target_addr = aliased(Address)
        
        query = (
            select(
                Alert._ident,
                Alert.messageid,
                DetectTime.time.label("detect_time"),
                CreateTime.time.label("create_time"),
                Classification.text.label("classification_text"),
                Impact.severity,
                source_addr.address.label("source_ipv4"),
                target_addr.address.label("target_ipv4"),
                Analyzer.name.label("analyzer_name"),
                Node.name.label("analyzer_host"),
                Analyzer.model.label("analyzer_model"),
            )
            .select_from(Alert)
            .outerjoin(DetectTime, DetectTime._message_ident == Alert._ident)
            .outerjoin(CreateTime, CreateTime._message_ident == Alert._ident)
            .outerjoin(Classification, Classification._message_ident == Alert._ident)
            .outerjoin(Impact, Impact._message_ident == Alert._ident)
            .outerjoin(
                source_addr, 
                and_(
                    source_addr._message_ident == Alert._ident,
                    source_addr._parent_type == "S",
                    source_addr._parent0_index == -1,
                    source_addr.category == "ipv4-addr",
                )
            )
            .outerjoin(
                target_addr, 
                and_(
                    target_addr._message_ident == Alert._ident,
                    target_addr._parent_type == "T",
                    target_addr._parent0_index == -1,
                    target_addr.category == "ipv4-addr",
                )
            )
            .outerjoin(
                Analyzer, 
                and_(
                    Analyzer._message_ident == Alert._ident,
                    Analyzer._parent_type == "A",
                    Analyzer._index == -1,
                )
            )
            .outerjoin(
                Node, 
                and_(
                    Node._message_ident == Alert._ident,
                    Node._parent_type == "A",
                    Node._parent0_index == -1,
                )
            )
            .group_by(Alert._ident)
            .order_by(DetectTime.time.desc())
            .limit(5)  # Limit to 5 for testing
        )
        
        print("Query SQL:")
        print(str(query))
        print("\nExecuting query...")
        
        # Try different execution methods
        try:
            # Method 1: Regular execute
            print("\nMethod 1: Regular execute")
            result = db.execute(query)
            rows = result.fetchall()
            print(f"Got {len(rows)} rows")
            if rows:
                print(f"First row has {len(rows[0])} columns")
                print(f"First row: {rows[0][:3]}...")  # Print first 3 columns
        except Exception as e:
            print(f"Method 1 failed: {e}")
            
        try:
            # Method 2: With yield_per
            print("\nMethod 2: With yield_per execution option")
            result = db.execute(query, execution_options={"yield_per": 100})
            count = 0
            for row in result:
                count += 1
                if count == 1:
                    print(f"First row has {len(row)} columns")
                    print(f"First row: {row[:3]}...")
                if count >= 3:
                    break
            print(f"Processed {count} rows with yield_per")
        except Exception as e:
            print(f"Method 2 failed: {e}")

if __name__ == "__main__":
    test_export_query()
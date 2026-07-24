"""
PROCUREMENT DATA STRUCTURING MODULE
Eximp & Cloves Infrastructure Limited - ERP System
====================================================

Intelligent parsing of quotations and procurement documents.
Extracts, validates, and structures procurement data for database insertion.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from decimal import Decimal
import re
from dataclasses import dataclass

@dataclass
class ProcurementItem:
    """Represents a single procurement line item"""
    sn: int
    description: str
    quantity: float
    quantity_unit: str
    unit_price: Decimal
    amount: Decimal
    category: str
    section: str
    
    def to_dict(self):
        return {
            'sn': self.sn,
            'description': self.description,
            'quantity': self.quantity,
            'quantity_unit': self.quantity_unit,
            'unit_price': float(self.unit_price),
            'amount': float(self.amount),
            'category': self.category,
            'section': self.section
        }


@dataclass
class ProcurementSection:
    """Represents a section of the quotation (e.g., Fencing, Site Clearing)"""
    name: str
    items: List[ProcurementItem]
    total_amount: Decimal
    description: str = ""
    
    @property
    def item_count(self):
        return len(self.items)
    
    @property
    def categories(self):
        return list(set(item.category for item in self.items))
    
    def to_dict(self):
        return {
            'name': self.name,
            'description': self.description,
            'items': [item.to_dict() for item in self.items],
            'item_count': self.item_count,
            'total_amount': float(self.total_amount),
            'categories': self.categories
        }


class QuotationParser:
    """
    Intelligent quotation parser.
    Maps procurement items to business categories and validates data.
    """
    
    # Category mapping rules
    CATEGORY_KEYWORDS = {
        'Materials & Supplies': ['cement', 'blocks', 'sand', 'gravel', 'wire', 'rods', 'containers'],
        'Equipment & Machinery': ['excavator', 'loader', 'truck', 'crane', 'generator'],
        'Labour & Services': ['labour', 'workers', 'accommodation', 'feeding', 'transportation'],
        'Miscellaneous': ['miscellaneous', 'contingency', 'misc']
    }
    
    QUANTITY_UNITS = {
        'units': ['units', 'no', 'nos', 'pcs', 'pieces'],
        'weight': ['tons', 'tonnes', 'kg', 'kilograms'],
        'volume': ['cubic', 'm3', 'cbm'],
        'time': ['days', 'weeks', 'months', 'hours'],
        'other': ['__', '—', '', None]
    }
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.raw_df = None
        self.sections: List[ProcurementSection] = []
        self.metadata = {}
        
    def parse(self) -> Tuple[List[ProcurementSection], Dict]:
        """Main parsing method"""
        self._load_raw_data()
        self._extract_metadata()
        self._extract_sections()
        return self.sections, self.metadata
    
    def _load_raw_data(self):
        """Load Excel file"""
        self.raw_df = pd.read_excel(self.filepath, sheet_name=0, header=None)
        print(f"✓ Loaded quotation file: {self.filepath}")
        print(f"  Dimensions: {self.raw_df.shape}")
    
    def _extract_metadata(self):
        """Extract header metadata"""
        df = self.raw_df
        
        # Extract metadata from first rows
        for idx, row in df.iterrows():
            row_text = ' '.join([str(v) for v in row if pd.notna(v)]).strip()
            
            if 'Company Name:' in row_text:
                self.metadata['company'] = row_text.split('Company Name:')[1].strip()
            elif 'Project Location:' in row_text:
                self.metadata['location'] = row_text.split('Project Location:')[1].strip()
            elif 'Date:' in row_text:
                date_str = row_text.split('Date:')[1].strip()
                self.metadata['quotation_date'] = self._parse_date(date_str)
            elif 'Quotation No' in row_text:
                self.metadata['quotation_number'] = row_text.split('Quotation No')[-1].strip()
        
        # Set defaults
        self.metadata.setdefault('company', 'EXIMPS & CLOVES INFRASTRUCTURE LIMITED')
        self.metadata.setdefault('location', 'Project Site')
        self.metadata.setdefault('quotation_date', datetime.now().strftime('%Y-%m-%d'))
        
        print(f"✓ Metadata extracted:")
        for key, val in self.metadata.items():
            print(f"  {key}: {val}")
    
    def _extract_sections(self):
        """Extract procurement sections from the quotation"""
        df = self.raw_df.fillna('')
        
        section_starts = []
        current_section = None
        items_data = []
        
        for idx, row in df.iterrows():
            row_text = ' '.join([str(v) for v in row if v != '']).strip().upper()
            
            # Detect section headers
            if any(keyword in row_text for keyword in ['QUOTATION', 'WORKS', 'SECTION', 'CATEGORY']):
                # Save previous section if exists
                if current_section and items_data:
                    section = self._create_section(current_section, items_data)
                    if section:
                        self.sections.append(section)
                    items_data = []
                
                current_section = row_text
                section_starts.append((idx, current_section))
            
            # Detect table header (S/N, ITEMS DESCRIPTION, QUANTITY, UNIT PRICE, AMOUNT)
            elif all(keyword in row_text for keyword in ['S/N', 'DESCRIPTION', 'QUANTITY', 'UNIT PRICE', 'AMOUNT']):
                continue
            
            # Detect data rows (S/N is numeric)
            elif row[0] != '' and str(row[0]).isdigit():
                items_data.append(row)
            
            # Detect total line
            elif 'TOTAL' in row_text and any(str(v).replace(',', '').isdigit() for v in row if v != ''):
                if items_data and current_section:
                    section = self._create_section(current_section, items_data)
                    if section:
                        self.sections.append(section)
                    items_data = []
                    current_section = None
        
        # Process last section if exists
        if current_section and items_data:
            section = self._create_section(current_section, items_data)
            if section:
                self.sections.append(section)
        
        print(f"✓ Extracted {len(self.sections)} procurement sections")
    
    def _create_section(self, section_name: str, rows) -> Optional[ProcurementSection]:
        """Create a procurement section from rows"""
        items = []
        total_amount = Decimal(0)
        
        for row in rows:
            try:
                sn = int(row[0]) if pd.notna(row[0]) else None
                description = str(row[1]).strip() if pd.notna(row[1]) else ""
                qty_raw = str(row[2]).strip() if pd.notna(row[2]) else "0"
                unit_price_raw = str(row[3]).strip() if pd.notna(row[3]) else "0"
                amount_raw = str(row[4]).strip() if pd.notna(row[4]) else "0"
                
                # Parse quantity and unit
                qty, qty_unit = self._parse_quantity(qty_raw)
                
                # Parse prices
                unit_price = self._parse_currency(unit_price_raw)
                amount = self._parse_currency(amount_raw)
                
                if qty > 0 and amount > 0 and description:
                    # Categorize item
                    category = self._categorize_item(description)
                    
                    item = ProcurementItem(
                        sn=sn,
                        description=description,
                        quantity=qty,
                        quantity_unit=qty_unit,
                        unit_price=unit_price,
                        amount=amount,
                        category=category,
                        section=section_name.title()
                    )
                    items.append(item)
                    total_amount += amount
            except Exception as e:
                print(f"  ⚠ Error parsing row {row}: {e}")
                continue
        
        if items:
            section = ProcurementSection(
                name=section_name.replace('QUOTATION FOR', '').replace('QUOTATION', '').strip().title(),
                items=items,
                total_amount=total_amount,
                description=section_name
            )
            print(f"  ✓ Section '{section.name}': {len(items)} items, ₦{total_amount:,.0f}")
            return section
        
        return None
    
    @staticmethod
    def _parse_date(date_str: str) -> str:
        """Parse date string"""
        formats = ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%m/%d/%Y']
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime('%Y-%m-%d')
            except:
                continue
        return datetime.now().strftime('%Y-%m-%d')
    
    @staticmethod
    def _parse_currency(value: str) -> Decimal:
        """Parse currency value"""
        if not value or value in ['__', '—', 'N/A']:
            return Decimal(0)
        # Remove commas and currency symbols
        cleaned = re.sub(r'[₦,\s]', '', str(value))
        try:
            return Decimal(cleaned)
        except:
            return Decimal(0)
    
    @staticmethod
    def _parse_quantity(qty_str: str) -> Tuple[float, str]:
        """Parse quantity with unit"""
        if not qty_str or qty_str in ['__', '—']:
            return 0, 'units'
        
        qty_str = qty_str.strip().lower()
        
        # Try to extract numeric part
        match = re.match(r'([\d.]+)\s*(.*)', qty_str)
        if match:
            qty = float(match.group(1))
            unit = match.group(2).strip() if match.group(2) else 'units'
        else:
            return 0, 'units'
        
        return qty, unit
    
    def _categorize_item(self, description: str) -> str:
        """Categorize item based on description"""
        desc_lower = description.lower()
        
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            if any(keyword in desc_lower for keyword in keywords):
                return category
        
        return 'Other Services'
    
    def get_summary(self) -> Dict:
        """Get parsed data summary"""
        total_items = sum(s.item_count for s in self.sections)
        total_amount = sum(s.total_amount for s in self.sections)
        
        return {
            'metadata': self.metadata,
            'sections': [s.to_dict() for s in self.sections],
            'summary': {
                'total_sections': len(self.sections),
                'total_items': total_items,
                'total_amount': float(total_amount),
                'sections_breakdown': {s.name: float(s.total_amount) for s in self.sections}
            }
        }


if __name__ == "__main__":
    # Test the parser
    filepath = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\eximps-cloves quotation.xlsx'
    
    parser = QuotationParser(filepath)
    sections, metadata = parser.parse()
    
    print("\n" + "="*70)
    print("PROCUREMENT DATA STRUCTURE")
    print("="*70)
    
    summary = parser.get_summary()
    print(f"\n✓ Quotation Date: {summary['metadata']['quotation_date']}")
    print(f"✓ Location: {summary['metadata']['location']}")
    print(f"✓ Total Sections: {summary['summary']['total_sections']}")
    print(f"✓ Total Items: {summary['summary']['total_items']}")
    print(f"✓ Total Amount: ₦{summary['summary']['total_amount']:,.2f}\n")
    
    for section in sections:
        print(f"\n📦 Section: {section.name}")
        print(f"   Total: ₦{section.total_amount:,.2f}")
        print(f"   Categories: {', '.join(section.categories)}")
        print(f"\n   Items:")
        for item in section.items:
            print(f"   {item.sn}. {item.description}")
            print(f"      Qty: {item.quantity} {item.quantity_unit} | Unit: ₦{item.unit_price:,.0f} | Amount: ₦{item.amount:,.0f}")

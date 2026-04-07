content = open('templates/payouts_dashboard.html', encoding='utf-8').read()

checks = {
    'Verification tab': 'verif-tab' in content,
    'Bill Verification view': 'verification-view' in content,
    'verifBody': 'verifBody' in content,
    'bill-search-wrap': 'bill-search-wrap' in content,
    'pay-bill-search input': 'pay-bill-search' in content,
    'filterBillSearch fn': 'filterBillSearch' in content,
    'selectBill fn': 'selectBill' in content,
    'renderVerifications fn': 'renderVerifications' in content,
    'renderVerifications call': 'renderVerifications(requestsData)' in content,
    'verifyBill fn': 'verifyBill' in content,
    'payableBills var': 'payableBills =' in content,
    'hidden pay-request-id': 'type="hidden" id="pay-request-id"' in content,
}

for k, v in checks.items():
    mark = 'OK  ' if v else 'FAIL'
    print(f'  [{mark}] {k}')

print(f'\nTotal lines: {content.count(chr(10))}')

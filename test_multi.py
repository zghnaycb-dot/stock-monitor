import sys
sys.path.insert(0, 'src')
from multi_source import get_manager

mgr = get_manager()

print('=== Realtime ===')
quotes = mgr.get_realtime(['600519', '000001'])
print('Count:', len(quotes))
for q in quotes:
    code = q.get('code', '?')
    name = q.get('name', '?')
    current = q.get('current', 0)
    pct = q.get('pct', 0)
    source = q.get('source', '?')
    print('  %s %s: %s (%s%%) [%s]' % (code, name, current, pct, source))

print()
print('=== Market Top ===')
gainers = mgr.get_market_top('gainers', 3)
print('Gainers:', len(gainers))
for g in gainers:
    code = g.get('code', '?')
    name = g.get('name', '?')
    pct = g.get('pct', 0)
    source = g.get('source', '?')
    print('  %s %s: %s%% [%s]' % (code, name, pct, source))

print()
print('=== News ===')
news = mgr.get_news(3)
print('News:', len(news))
for n in news:
    title = n.get('title', '?')[:50]
    source = n.get('source', '?')
    print('  %s [%s]' % (title, source))

print()
print('=== Health ===')
report = mgr.get_health_report()
for name, status in report.items():
    ok = status.get('ok', False)
    print('  %s: %s' % (name, ok))

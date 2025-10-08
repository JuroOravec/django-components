from statistics import mean, stdev
import time

from djc_template_parser import parse_tag
from django_components.util.tag_parser import parse_tag as django_parse_tag  # TODO DELETE

# Complex test case with nested structures, filters, spreads and translations
TEST_CASE = """
    component
    data={
        "items": [
            1|add:2,
            {"x"|upper: 2|add:3},
            *spread_items|default:""
        ],
        "nested": {
            "a": [
                1|add:2,
                *nums|default:""
            ],
            "b": {
                "x": [
                    *more|default:""
                ]
            }
        },
        **rest|default,
        "key": _('value')|upper
    }
"""

NUM_ITER = 1000  # Number of iterations for benchmarking
print("\nBenchmarking tag parser with complex test case")
print(f"Test case length: {len(TEST_CASE)} characters")

# Test parsing performance
parse_times = []
for i in range(NUM_ITER):
    start = time.perf_counter()
    # parse_tag(TEST_CASE) # TODO
    django_parse_tag(TEST_CASE)
    parse_time = time.perf_counter() - start
    parse_times.append(parse_time)

print("\nParse times:")
print(f"  Total: {sum(parse_times):.3f}s")
print(f"  Min: {min(parse_times):.3f}s")
print(f"  Max: {max(parse_times):.3f}s")
print(f"  Avg: {mean(parse_times):.3f}s")
print(f"  Std: {stdev(parse_times):.3f}s")

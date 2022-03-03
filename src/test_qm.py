from quine_mccluskey.qm import QuineMcCluskey

patterns = ['0001', '0010', '0101', '0110', '1001', '1010' '1101', '1110']

# help(QuineMcCluskey())
res2 = QuineMcCluskey().simplify([2, 6, 10, 14, 15], num_bits=5)

print(res2)
# print(type(res2))


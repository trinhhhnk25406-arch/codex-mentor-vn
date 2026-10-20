students = ["Hoàng", "Mai", "Nam"]

# Vòng lặp duyệt danh sách cố tình sai điều kiện biên (+1)
for i in range(len(students) + 1):
    print(f"Học sinh {i + 1}: {students[i]}")

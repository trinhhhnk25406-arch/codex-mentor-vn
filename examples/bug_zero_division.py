def calculate_average(scores: list[float]) -> float:
    # Hàm tính trung bình cộng điểm số của học sinh
    return sum(scores) / len(scores)

empty_scores = []
print("Điểm trung bình là:", calculate_average(empty_scores))

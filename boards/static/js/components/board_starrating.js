function starRating() {
  return {
    isOwner: false,
    rating: 0,
    hoverRating: 0,
    isHover: false,
    ratings: [1, 2, 3, 4, 5],
    rate(score) {
      if (!this.isOwner) {
        if (this.rating == score) {
          this.rating = 0;
        } else this.rating = score;
      }
    },
    starClass(score) {
      if (this.hoverRating >= score && this.hoverRating != 0) {
        return "bi-star-fill";
      } else if (this.rating >= score && this.hoverRating == 0) {
        return "bi-star-fill";
      } else {
        return "bi-star";
      }
    },
  };
}

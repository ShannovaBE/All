Manual Checklist (Owner-Only Delete + R2)

1. Start the API
   uvicorn main:app --reload
2. Upload a dataset
   - Confirm file appears in R2
   - Confirm row appears in Postgres (dataset_records)
3. Delete dataset as owner
   - R2 object removed
   - DB row removed
   - UI removes item
4. Attempt delete as non-owner
   - Expect 403 Forbidden

Manual Checklist (Reviews)

1. Run DB migrations (if needed)
   - From `backend/`: `alembic upgrade head`
2. Start the API
   - `uvicorn main:app --reload`
3. Create 2 users
   - Use the UI `/register` twice (or call `POST /register`)
4. Submit a review (signed in)
   - Go to `/reviews`, submit a 1-5 star review with non-empty text
   - Confirm it is saved as `pending` (use admin page or DB)
5. Confirm it is not public
   - `/reviews` should NOT show it until an admin makes it visible
6. Make it visible as admin
   - Set `ADMIN_USERNAMES=your_admin_username` in `backend/.env`
   - Visit `/admin/reviews` and make the pending review visible
7. Confirm it is now public
   - `/reviews` should show the review and update the average + count
8. Rate limiting
   - Try submitting updates rapidly; expect a `429` with a short wait message
9. Review visibility window
   - Reviews are public for `REVIEW_VISIBILITY_MONTHS` (default 24) after being made visible.
   - Older reviews become archived (not public) but remain in the admin list.


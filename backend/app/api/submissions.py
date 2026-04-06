import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.challenge import Challenge
from app.models.instance import Instance, InstanceStatus
from app.models.submission import Submission
from app.models.user import User
from app.schemas.submission import ScoreboardEntry, SubmissionCreate, SubmissionResponse

router = APIRouter()


@router.post("/", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
async def submit_flag(
    body: SubmissionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubmissionResponse:
    challenge_result = await db.execute(
        select(Challenge).where(Challenge.id == body.challenge_id)
    )
    challenge = challenge_result.scalar_one_or_none()
    if challenge is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Challenge not found",
        )

    # Find user's active (RUNNING) instance for the challenge's box
    instance_result = await db.execute(
        select(Instance).where(
            Instance.user_id == user.id,
            Instance.box_id == challenge.box_id,
            Instance.status == InstanceStatus.RUNNING.value,
        )
    )
    instance = instance_result.scalar_one_or_none()
    if instance is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active instance for this challenge's box",
        )

    # Parse flags_json and compare
    flags: dict[str, str] = {}
    if instance.flags_json:
        flags = json.loads(instance.flags_json) if isinstance(instance.flags_json, str) else instance.flags_json

    expected_flag = flags.get(challenge.flag_prefix)
    is_correct = expected_flag is not None and body.flag == expected_flag

    # Check if already solved (prevent duplicate correct submissions)
    if is_correct:
        already_solved_result = await db.execute(
            select(Submission).where(
                Submission.user_id == user.id,
                Submission.challenge_id == body.challenge_id,
                Submission.is_correct.is_(True),
            )
        )
        if already_solved_result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Challenge already solved",
            )

    submission = Submission(
        user_id=user.id,
        challenge_id=body.challenge_id,
        flag_submitted=body.flag,
        is_correct=is_correct,
    )
    db.add(submission)
    await db.flush()

    return SubmissionResponse.model_validate(submission)


@router.get("/", response_model=list[SubmissionResponse])
async def list_submissions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SubmissionResponse]:
    result = await db.execute(
        select(Submission)
        .where(Submission.user_id == user.id)
        .order_by(Submission.submitted_at.desc())
    )
    submissions = result.scalars().all()
    return [SubmissionResponse.model_validate(s) for s in submissions]


@router.get("/scoreboard", response_model=list[ScoreboardEntry])
async def scoreboard(db: AsyncSession = Depends(get_db)) -> list[ScoreboardEntry]:
    # Aggregate correct submissions: sum points per user
    query = (
        select(
            User.username,
            func.coalesce(func.sum(Challenge.points), 0).label("total_score"),
            func.count(Submission.id).label("solved_count"),
        )
        .join(Submission, Submission.user_id == User.id)
        .join(Challenge, Challenge.id == Submission.challenge_id)
        .where(Submission.is_correct.is_(True))
        .group_by(User.id, User.username)
        .order_by(func.sum(Challenge.points).desc())
    )
    result = await db.execute(query)
    rows = result.all()

    return [
        ScoreboardEntry(
            username=row.username,
            total_score=int(row.total_score),
            solved_count=int(row.solved_count),
        )
        for row in rows
    ]

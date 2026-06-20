"""Multi-stage robot arm motion simulation."""

import asyncio

from robot_arm import MultiStageMotionOrchestrator, RobotArmConfig
from robot_arm.simulated import SimulatedMotorDriver, SimulatedPositionFeedback
from robot_arm.stages import MotionStage, StageProgressInfo


class ConsoleProgressCallback:
  def on_stage_progress(self, progress_info: StageProgressInfo) -> None:
      stage = progress_info.stage.value
      status = progress_info.status.value
      duration = ""
      if progress_info.stage_result:
          duration = f" ({progress_info.stage_result.duration:.3f}s)"
      print(f"  [{status}] {stage}{duration}")


async def main() -> None:
    config = RobotArmConfig.for_testing()
    feedback = SimulatedPositionFeedback(horizontal=0.0, vertical=500.0)
    motor = SimulatedMotorDriver(feedback, step_size=20.0, move_delay=0.005)

    orchestrator = MultiStageMotionOrchestrator(
        feedback=feedback,
        motor=motor,
        config=config,
        progress_callback=ConsoleProgressCallback(),
    )

    target_slot = "B2"
    print(f"Moving to slot {target_slot}...")
    pos = feedback.read_position()
    print(f"Start position: h={pos.horizontal}, v={pos.vertical}")

    result = await orchestrator.move_to_slot(target_slot)

    end = feedback.read_position()
    print(f"\nResult: {'SUCCESS' if result.success else 'FAILED'}")
    print(f"Duration: {result.total_duration:.3f}s")
    print(f"Final position: h={end.horizontal}, v={end.vertical}")
    print(f"Stages completed: {len(result.stage_results)}/{len(MotionStage)}")


if __name__ == "__main__":
    asyncio.run(main())

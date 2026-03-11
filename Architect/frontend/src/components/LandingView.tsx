import { useMemo, useState } from "react";

interface LandingViewProps {
  prompt: string;
  disabled: boolean;
  onSubmit: (payload: string) => void;
}

const USER_OPTIONS = ["男", "女", "无所谓"] as const;
const AVATAR_OPTIONS = ["男", "女", "他者", "随世界定"] as const;

export function LandingView({ prompt, disabled, onSubmit }: LandingViewProps) {
  const [userGender, setUserGender] = useState<(typeof USER_OPTIONS)[number]>("男");
  const [avatarGender, setAvatarGender] = useState<(typeof AVATAR_OPTIONS)[number]>("男");

  const payload = useMemo(
    () => `我的性别是${userGender}，在这个世界里推开那扇门的化身是${avatarGender}。`,
    [avatarGender, userGender],
  );

  return (
    <section className="full-screen-panel landing-view">
      <p className="landing-view__prompt">{prompt}</p>
      <fieldset className="landing-view__group">
        <legend>你的性别</legend>
        <div className="landing-view__options">
          {USER_OPTIONS.map((option) => (
            <label key={option}>
              <input
                type="radio"
                name="user-gender"
                value={option}
                checked={userGender === option}
                onChange={() => setUserGender(option)}
              />
              <span>{option}</span>
            </label>
          ))}
        </div>
      </fieldset>
      <fieldset className="landing-view__group">
        <legend>化身性别</legend>
        <div className="landing-view__options">
          {AVATAR_OPTIONS.map((option) => (
            <label key={option}>
              <input
                type="radio"
                name="avatar-gender"
                value={option}
                checked={avatarGender === option}
                onChange={() => setAvatarGender(option)}
              />
              <span>{option}</span>
            </label>
          ))}
        </div>
      </fieldset>
      <button className="action-button" type="button" disabled={disabled} onClick={() => onSubmit(payload)}>
        开始
      </button>
    </section>
  );
}


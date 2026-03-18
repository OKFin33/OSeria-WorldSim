import { useState } from "react";
import { LoadingSpinner } from "./LoadingSpinner";
import type { LandingPayload } from "../types";

interface LandingViewProps {
  prompt: string;
  disabled: boolean;
  isWaiting?: boolean;
  waitingPhrase?: string | null;
  onSubmit: (payload: LandingPayload) => void;
}

const USER_OPTIONS = ["男", "女", "其他"] as const;
const AVATAR_OPTIONS = ["男", "女", "其他", "世界提供"] as const;
const NAME_MODE_OPTIONS = [
  { value: "custom", label: "我自己命名" },
  { value: "generated", label: "世界提供" },
] as const;

export function LandingView({ prompt, disabled, isWaiting = false, waitingPhrase = null, onSubmit }: LandingViewProps) {
  const [userGender, setUserGender] = useState<(typeof USER_OPTIONS)[number]>("男");
  const [avatarGender, setAvatarGender] = useState<(typeof AVATAR_OPTIONS)[number]>("男");
  const [nameMode, setNameMode] = useState<(typeof NAME_MODE_OPTIONS)[number]["value"]>("generated");
  const [customName, setCustomName] = useState("");

  const trimmedName = customName.trim();
  const customNameInvalid = nameMode === "custom" && !trimmedName;
  const submitDisabled = disabled || customNameInvalid;

  function handleSubmit() {
    if (submitDisabled) {
      return;
    }
    const payload: LandingPayload = {
      user_gender: userGender,
      avatar_gender: avatarGender,
      name_mode: nameMode,
    };
    if (nameMode === "custom") {
      payload.custom_name = trimmedName;
    }
    onSubmit(payload);
  }

  return (
    <section className="full-screen-panel landing-view">
      {!isWaiting ? <p className="landing-view__prompt">{prompt}</p> : null}
      {isWaiting && waitingPhrase ? (
        <p className="waiting-copy waiting-copy--panel" aria-live="polite" key={waitingPhrase}>
          <span className="waiting-copy__inner">{waitingPhrase}</span>
        </p>
      ) : null}
      {!isWaiting ? (
        <>
          <fieldset className="landing-view__group">
            <legend>你的性别</legend>
            <div className="landing-view__options">
              {USER_OPTIONS.map((option) => (
                <label key={option} className="landing-view__option">
                  <input
                    type="radio"
                    name="user-gender"
                    value={option}
                    checked={userGender === option}
                    onChange={() => setUserGender(option)}
                  />
                  <span className="landing-view__ink-dot" aria-hidden="true" />
                  <span className="landing-view__option-label">{option}</span>
                </label>
              ))}
            </div>
          </fieldset>
          <fieldset className="landing-view__group">
            <legend>主角性别</legend>
            <div className="landing-view__options">
              {AVATAR_OPTIONS.map((option) => (
                <label key={option} className="landing-view__option">
                  <input
                    type="radio"
                    name="avatar-gender"
                    value={option}
                    checked={avatarGender === option}
                    onChange={() => setAvatarGender(option)}
                  />
                  <span className="landing-view__ink-dot" aria-hidden="true" />
                  <span className="landing-view__option-label">{option}</span>
                </label>
              ))}
            </div>
          </fieldset>
          <fieldset className="landing-view__group">
            <legend>你想怎么确定主角名字？</legend>
            <div className="landing-view__options">
              {NAME_MODE_OPTIONS.map((option) => (
                <label key={option.value} className="landing-view__option">
                  <input
                    type="radio"
                    name="name-mode"
                    value={option.value}
                    checked={nameMode === option.value}
                    onChange={() => setNameMode(option.value)}
                  />
                  <span className="landing-view__ink-dot" aria-hidden="true" />
                  <span className="landing-view__option-label">{option.label}</span>
                </label>
              ))}
            </div>
          </fieldset>
          {nameMode === "custom" ? (
            <label className="landing-view__group">
              <span>主角名字</span>
              <input
                className="input-area__field"
                type="text"
                value={customName}
                onChange={(event) => setCustomName(event.target.value)}
                placeholder="输入主角名字"
                maxLength={16}
              />
              {customNameInvalid ? <small className="landing-view__hint">名字不能为空。</small> : null}
            </label>
          ) : null}
        </>
      ) : null}
      <button
        className={`action-button${isWaiting ? " action-button--loading" : ""}`}
        type="button"
        disabled={submitDisabled}
        onClick={handleSubmit}
        aria-label={isWaiting ? "正在开始" : "开始"}
      >
        {isWaiting ? <LoadingSpinner label="正在开始" /> : "开始"}
      </button>
    </section>
  );
}

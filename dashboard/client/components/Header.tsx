"use client";
import { motion } from "framer-motion";
import { BEIHANG } from "@/lib/colors";
import { FiWifi, FiWifiOff } from "@/lib/icons";
import { FiVolume2, FiVolumeX } from "react-icons/fi";
import { useT, LANGS } from "@/lib/i18n";

export default function Header({ minimal, onToggle, connected, muted, onToggleMute }: {
  minimal: boolean;
  onToggle: () => void;
  connected: boolean;
  muted: boolean;
  onToggleMute: () => void;
}) {
  const { t, lang, setLang } = useT();
  return (
    <header
      className="sticky top-0 z-30 border-b border-white/10 px-6 py-4 backdrop-blur"
      style={{ background: `linear-gradient(110deg, ${BEIHANG.primary} 0%, #06294d 60%, ${BEIHANG.secondary} 140%)` }}
    >
      <div className="mx-auto flex max-w-[1640px] items-center gap-4">
        <div className="flex items-center gap-3">
          <LogoChip src="/B logo.png" alt="Beihang University" />
          <LogoChip src="/r logo.png" alt="RCSSTEAP" />
        </div>

        <div className="ml-1">
          <h1 className="text-xl font-extrabold leading-tight tracking-tight text-white md:text-2xl">
            SENTINEL&#8209;GNSS
          </h1>
          <p className="text-[12px] font-medium text-white/70">{t("subtitle")}</p>
        </div>

        <div className="ml-auto flex items-center gap-3">
          {/* connection */}
          <div className="hidden items-center gap-2 rounded-full bg-white/10 px-3 py-1.5 ring-1 ring-white/15 md:flex">
            <motion.span animate={{ opacity: connected ? [1, 0.45, 1] : 1 }} transition={{ repeat: Infinity, duration: 2 }} className="flex text-white">
              {connected ? <FiWifi size={15} /> : <FiWifiOff size={15} />}
            </motion.span>
            <span className="text-xs font-bold text-white/85">{connected ? t("live") : t("offline")}</span>
          </div>

          {/* language */}
          <div className="flex items-center gap-1.5 rounded-full bg-white/10 px-2 py-1 ring-1 ring-white/15">
            <span className="pl-1 text-sm">🌐</span>
            <select
              value={lang}
              onChange={(e) => setLang(e.target.value as typeof lang)}
              aria-label={t("language")}
              className="cursor-pointer bg-transparent py-1 pr-1 text-xs font-bold text-white outline-none [&>option]:text-black"
            >
              {LANGS.map((l) => (
                <option key={l.id} value={l.id}>{l.flag} {l.label}</option>
              ))}
            </select>
          </div>

          {/* sound */}
          <button
            onClick={onToggleMute}
            title={muted ? t("sound_off") : t("sound_on")}
            className="flex h-9 w-9 items-center justify-center rounded-full bg-white/10 text-white ring-1 ring-white/15 transition hover:bg-white/20"
          >
            {muted ? <FiVolumeX size={16} /> : <FiVolume2 size={16} />}
          </button>

          {/* extended / minimal */}
          <button
            onClick={onToggle}
            className="relative flex items-center rounded-full bg-white/10 p-1 text-xs font-bold text-white ring-1 ring-white/20"
            aria-label="Toggle view density"
          >
            <span className={`relative z-10 rounded-full px-3 py-1.5 transition ${minimal ? "text-white/60" : "text-white"}`}>{t("extended")}</span>
            <span className={`relative z-10 rounded-full px-3 py-1.5 transition ${minimal ? "text-white" : "text-white/60"}`}>{t("minimal")}</span>
            <motion.span layout transition={{ type: "spring", stiffness: 400, damping: 30 }}
              className="absolute top-1 bottom-1 rounded-full"
              style={{ background: BEIHANG.accent, left: minimal ? "calc(50%)" : 4, right: minimal ? 4 : "calc(50%)" }} />
          </button>
        </div>
      </div>
    </header>
  );
}

function LogoChip({ src, alt }: { src: string; alt: string }) {
  return (
    <div className="flex h-11 w-11 items-center justify-center overflow-hidden rounded-xl bg-white/95 p-1 shadow-md ring-1 ring-white/30">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={src} alt={alt} className="max-h-full max-w-full object-contain" />
    </div>
  );
}

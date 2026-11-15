import React from "react";
import {Composition} from "remotion";
import {Episode, EpisodeData} from "./Episode";
import {Logo} from "./Logo";
import ep01 from "./data/ep01.json";

const EPISODES: Record<string, EpisodeData> = {ep01: ep01 as EpisodeData};

export const Root: React.FC = () => (
  <>
    {Object.entries(EPISODES).map(([id, d]) => (
      <Composition key={id} id={id} component={Episode} defaultProps={{d}}
        durationInFrames={d.frames} fps={d.fps} width={1080} height={1920} />
    ))}
    {(["mark", "word", "ring"] as const).map((v) => (
      <Composition key={v} id={`logo-${v}`} component={Logo} defaultProps={{variant: v}}
        durationInFrames={1} fps={30} width={1080} height={1080} />
    ))}
  </>
);

// client/src/components/HomeAssistant/Devices/DeviceCard.tsx
import cn from '~/utils/cn';
import { motion } from 'framer-motion';
import CameraModal from '../Camera/CameraModal';
import useLocalize from '~/hooks/useLocalize';
import { useHACommand } from '~/hooks/useHomeAssistant';
import { HAEntity } from '~/common/home-assistant-types';
import { Badge, Button, Card, CardContent, Switch } from "~/components/ui/";
import React, { useMemo, useCallback, useState } from 'react';
import {
  Lightbulb, Power, Thermometer, Droplet, Battery, Activity,
  Camera, Fan, Lock, Tv, Speaker, Bell, Cloud, Clock, MapPin,
  Settings, DoorClosed, DoorOpen, Grid2x2, AlertCircle, Zap,
} from 'lucide-react';

interface DeviceCardProps {
  entity: HAEntity;
}

// Iconos por dominio
const domainIcons: Record<string, JSX.Element> = {
  light: <Lightbulb className="w-6 h-6 text-amber-400/80" />,
  switch: <Power className="w-6 h-6 text-sky-500/80" />,
  climate: <Thermometer className="w-6 h-6 text-red-500/80" />,
  humidifier: <Droplet className="w-6 h-6 text-blue-500/80" />,
  battery: <Battery className="w-6 h-6 text-yellow-500/80" />,
  camera: <Camera className="w-6 h-6 text-indigo-400/80" />,
  fan: <Fan className="w-6 h-6 text-cyan-400/80" />,
  lock: <Lock className="w-6 h-6 text-slate-500/80" />,
  media_player: <Tv className="w-6 h-6 text-purple-400/80" />,
  speaker: <Speaker className="w-6 h-6 text-violet-400/80" />,
  siren: <Bell className="w-6 h-6 text-rose-500/80" />,
  button: <Zap className="w-6 h-6 text-orange-400/80" />,
  weather: <Cloud className="w-6 h-6 text-sky-400/80" />,
  timer: <Clock className="w-6 h-6 text-emerald-400/80" />,
  zone: <MapPin className="w-6 h-6 text-teal-400/80" />,
  homeassistant: <Settings className="w-6 h-6 text-gray-500/80" />,
};


// Iconos dinámicos para sensores
const sensorIcons = (entity: HAEntity, domain: string) => {
  const id = entity.entity_id.toLowerCase()
  const attrs = entity.attributes || {}

  if (domain === "binary_sensor") {
    if (id.includes("door"))
      return entity.state === "on" ? (
        <DoorOpen className="size-5 text-red-500/80" />
      ) : (
        <DoorClosed className="size-5 text-green-500/80" />
      )
    if (id.includes("window"))
      return entity.state === "on" ? (
        <Grid2x2 className="size-5 text-blue-500/80" />
      ) : (
        <Grid2x2 className="size-5 text-gray-400" />
      )
    if (id.includes("motion"))
      return entity.state === "on" ? (
        <Activity className="size-5 text-orange-500/80 animate-pulse" />
      ) : (
        <Activity className="size-5 text-gray-400" />
      )
    if (id.includes("smoke") || id.includes("fire")) return <AlertCircle className="size-5 text-red-500/80" />
    if (id.includes("power") || id.includes("energy")) return <Power className="size-5 text-yellow-500/80" />
    return <Activity className="size-5 text-gray-400" />
  }

  if (domain === "sensor") {
    if (id.includes("temperature") || attrs.unit_of_measurement === "°C")
      return <Thermometer className="size-5 text-red-500/80" />
    if (id.includes("humidity") || attrs.unit_of_measurement === "%")
      return <Droplet className="size-5 text-blue-500/80" />
    if (id.includes("battery")) return <Battery className="size-5 text-yellow-500/80" />
    return <Activity className="size-5 text-gray-400" />
  }

  return domainIcons[domain] ?? <Activity className="size-5 text-gray-400" />
}

const SensorProgress: React.FC<{
  label: string
  value: number
  max?: number
  color?: string
}> = ({ label, value, max = 100, color }) => {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100))
  const unit = label === "Temperatura" ? "°C" : label === "Humedad" ? "%" : "%"

  return (
    <div className="w-full space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium text-muted-foreground">{label}</span>
        <span className="font-semibold text-foreground">
          {value}
          {unit}
        </span>
      </div>
      <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all duration-300", color ?? "bg-green-600 dark:bg-green-500")}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}

const DeviceCard: React.FC<DeviceCardProps> = ({ entity }) => {
  const localize = useLocalize();
  const { mutate, isLoading } = useHACommand()
  const isOn = entity.state === "on"
  const domain = entity.entity_id.split(".")[0]
  const friendlyName = entity.name || entity.entity_id

  const [cameraModalOpen, setCameraModalOpen] = useState(false);

  const icon = useMemo(() => sensorIcons(entity, domain), [entity, domain])

  const handleToggle = useCallback(() => {
    const canToggle = ["light", "switch", "fan", "lock"].includes(domain)
    if (!canToggle) return

    mutate({
      domain,
      service: isOn ? "turn_off" : "turn_on",
      entity_id: entity.entity_id,
    })
  }, [entity, isOn, mutate, domain])

  const isToggleable = ["light", "switch", "fan", "lock"].includes(domain)
  const isCamera = domain === 'camera' && entity.stream_url;

  return (
    <motion.div
      layout
      whileHover={{ scale: 1.02 }}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
      className="h-full"
    >
      <Card className="h-full flex flex-col border border-border/40 shadow-lg dark:shadow-none hover:shadow-xl hover:border-border/60 transition-all duration-300">
        <CardContent className="flex-1 p-4 space-y-3">
          {/* Icon and status badge */}
          <div className="flex items-start justify-between gap-2">
            <div
              className={cn(
                "flex items-center justify-center size-11 rounded-xl",
                "bg-muted/50 text-muted-foreground transition-all duration-300",
                isOn && isToggleable && "bg-primary/15 text-primary shadow-sm",
              )}
            >
              {icon}
            </div>

            <Badge variant={isOn ? "default" : "secondary"} className="text-xs font-medium">
              {entity.state.toUpperCase()}
            </Badge>
          </div>

          {/* Device name and domain */}
          <div className="space-y-1">
            <h4 className="font-medium text-base text-foreground truncate leading-tight">{friendlyName}</h4>
            <p className="text-xs text-muted-foreground capitalize">{domain.replace("_", " ")}</p>
          </div>

          {entity.attributes?.temperature !== undefined && (
            <SensorProgress
              label="Temperatura"
              value={entity.attributes.temperature}
              color="bg-red-500/80 dark:bg-red-500/70"
            />
          )}
          {entity.attributes?.humidity !== undefined && (
            <SensorProgress
              label="Humedad"
              value={entity.attributes.humidity}
              color="bg-blue-500/80 dark:bg-blue-500/70"
            />
          )}
          {entity.attributes?.battery_level !== undefined && (
            <SensorProgress
              label="Batería"
              value={entity.attributes.battery_level}
              color="bg-yellow-500/80 dark:bg-yellow-500/70"
            />
          )}

          {isToggleable && (
            <div className="flex items-center gap-2 w-full">
              <Button
                size="sm"
                variant={isOn ? "outline" : "default"}
                onClick={handleToggle}
                disabled={isLoading}
                className="flex-1"
              >
                {isOn ? localize("com_ha_turn_off") : localize("com_ha_turn_on")}
              </Button>

              <Switch
                checked={isOn}
                onChange={handleToggle}
                disabled={isLoading}
                className="shrink-0"
              />
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  )
}

export default DeviceCard;

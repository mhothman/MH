import { useState, useEffect, useCallback } from "react";
import { startTimer, stopTimer, getActiveTimer, discardTimer, getTimeEntries } from "../api/time-entries";
import { getMyPermissions, hasPermission, Permission, getOrganizations } from "../api";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "./ui/avatar";
import { toast } from "sonner";
import { Play, Square, X, Clock, History } from "lucide-react";
import { format, formatDistanceToNow } from "date-fns";

export const TimeTracker = ({ taskId, taskTitle, onTimeLogged, canTrackTime = true, estimatedHours }) => {
  const [activeTimer, setActiveTimer] = useState(null);
  const [elapsed, setElapsed] = useState(0);
  const [loading, setLoading] = useState(false);
  const [timeLogs, setTimeLogs] = useState([]);
  const [showLogs, setShowLogs] = useState(true);

  // Fetch time entries for this task
  const loadTimeLogs = useCallback(async () => {
    try {
      const entries = await getTimeEntries(taskId);
      setTimeLogs(entries || []);
    } catch (error) {
      console.error("Failed to load time entries:", error);
    }
  }, [taskId]);

  const checkActiveTimer = useCallback(async () => {
    try {
      const response = await getActiveTimer();
      // API returns {active: boolean, timer: object|null}
      if (response && response.active && response.timer && response.timer.task_id === taskId) {
        setActiveTimer(response.timer);
      } else {
        setActiveTimer(null);
      }
    } catch (error) {
      console.error("Failed to check timer:", error);
      setActiveTimer(null);
    }
  }, [taskId]);

  useEffect(() => {
    checkActiveTimer();
    loadTimeLogs();
  }, [checkActiveTimer, loadTimeLogs]);

  useEffect(() => {
    if (!activeTimer || !activeTimer.started_at) {
      setElapsed(0);
      return;
    }

    const startedAt = new Date(activeTimer.started_at);
    
    // Check if date is valid
    if (isNaN(startedAt.getTime())) {
      setElapsed(0);
      return;
    }
    
    const updateElapsed = () => {
      const now = new Date();
      const diff = Math.floor((now - startedAt) / 1000);
      setElapsed(diff > 0 ? diff : 0);
    };

    updateElapsed();
    const interval = setInterval(updateElapsed, 1000);

    return () => clearInterval(interval);
  }, [activeTimer]);

  const formatTime = (seconds) => {
    if (isNaN(seconds) || seconds < 0) return "0:00";
    
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hrs > 0) {
      return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleStart = async () => {
    setLoading(true);
    try {
      const timer = await startTimer(taskId);
      setActiveTimer(timer);
      toast.success("Timer started");
    } catch (error) {
      toast.error(error.message || "Failed to start timer");
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      const result = await stopTimer();
      setActiveTimer(null);
      toast.success(`Logged ${result.hours_logged} hours`);
      if (onTimeLogged) onTimeLogged(result.hours_logged);
    } catch (error) {
      toast.error(error.message || "Failed to stop timer");
    } finally {
      setLoading(false);
    }
  };

  const handleDiscard = async () => {
    setLoading(true);
    try {
      await discardTimer();
      setActiveTimer(null);
      toast.info("Timer discarded");
    } catch (error) {
      toast.error(error.message || "Failed to discard timer");
    } finally {
      setLoading(false);
    }
  };

  // Don't render if user doesn't have permission
  if (!canTrackTime && !activeTimer) {
    return null;
  }

  if (activeTimer) {
    return (
      <div className="flex items-center gap-2 p-2 bg-primary/10 rounded-md" data-testid="active-timer">
        <Clock className="w-4 h-4 text-primary animate-pulse" />
        <Badge variant="secondary" className="font-mono text-sm">
          {formatTime(elapsed)}
        </Badge>
        <Button
          size="sm"
          variant="destructive"
          onClick={handleStop}
          disabled={loading}
          data-testid="stop-timer-btn"
        >
          <Square className="w-3 h-3 mr-1" />
          Stop
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={handleDiscard}
          disabled={loading}
          data-testid="discard-timer-btn"
        >
          <X className="w-3 h-3" />
        </Button>
      </div>
    );
  }

  return (
    <Button
      size="sm"
      variant="outline"
      onClick={handleStart}
      disabled={loading}
      data-testid="start-timer-btn"
    >
      <Play className="w-3 h-3 mr-1" />
      Start Timer
    </Button>
  );
};

// Global timer indicator for the header
export const GlobalTimerIndicator = () => {
  const [activeTimer, setActiveTimer] = useState(null);
  const [elapsed, setElapsed] = useState(0);
  
  // Check authentication status synchronously on initial render
  const hasToken = () => Boolean(localStorage.getItem('proflow_token'));

  useEffect(() => {
    // Don't start polling if no token
    if (!hasToken()) {
      return;
    }

    let isMounted = true;
    let interval;

    const checkTimer = async () => {
      // Check token before each request
      if (!hasToken()) {
        if (isMounted) {
          setActiveTimer(null);
        }
        if (interval) clearInterval(interval);
        return;
      }

      try {
        const response = await getActiveTimer();
        if (!isMounted) return;
        
        // API returns {active: boolean, timer: object|null}
        if (response && response.active && response.timer) {
          setActiveTimer(response.timer);
        } else {
          setActiveTimer(null);
        }
      } catch (error) {
        if (!isMounted) return;
        
        // Check if it's a 401 unauthorized error - stop polling
        if (error.status === 401) {
          setActiveTimer(null);
          if (interval) clearInterval(interval);
          return;
        }
        console.error("Failed to check timer:", error);
        setActiveTimer(null);
      }
    };

    checkTimer();
    interval = setInterval(checkTimer, 30000); // Check every 30 seconds

    return () => {
      isMounted = false;
      if (interval) clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    if (!activeTimer || !activeTimer.started_at) {
      return;
    }

    const startedAt = new Date(activeTimer.started_at);
    
    // Check if date is valid
    if (isNaN(startedAt.getTime())) {
      return;
    }
    
    const updateElapsed = () => {
      const now = new Date();
      const diff = Math.floor((now - startedAt) / 1000);
      setElapsed(diff > 0 ? diff : 0);
    };

    updateElapsed();
    const interval = setInterval(updateElapsed, 1000);

    return () => clearInterval(interval);
  }, [activeTimer]);

  const formatTime = (seconds) => {
    if (isNaN(seconds) || seconds < 0) return "0:00";
    
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hrs > 0) {
      return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleStop = async () => {
    try {
      const result = await stopTimer();
      setActiveTimer(null);
      toast.success(`Logged ${result.duration_minutes || 0} minutes`);
    } catch (error) {
      toast.error(error.message || "Failed to stop timer");
    }
  };

  if (!activeTimer) return null;

  return (
    <div className="flex items-center gap-2 px-3 py-1 bg-green-500/10 border border-green-500/30 rounded-full" data-testid="global-timer">
      <Clock className="w-4 h-4 text-green-500 animate-pulse" />
      <span className="font-mono text-sm text-green-600 dark:text-green-400">
        {formatTime(elapsed)}
      </span>
      <button
        onClick={handleStop}
        className="p-1 hover:bg-green-500/20 rounded-full transition-colors"
        data-testid="global-stop-timer-btn"
      >
        <Square className="w-3 h-3 text-green-600 dark:text-green-400" />
      </button>
    </div>
  );
};

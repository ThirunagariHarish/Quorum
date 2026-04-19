"use client";

import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import api, { type Deadline } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { Calendar, ExternalLink, Loader2, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

function daysUntil(deadline: string) {
  const diff = new Date(deadline).getTime() - Date.now();
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

export default function DeadlinesPage() {
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const [venueName, setVenueName] = useState("");
  const [venueType, setVenueType] = useState("conference");
  const [deadlineDate, setDeadlineDate] = useState("");
  const [venueUrl, setVenueUrl] = useState("");
  const [formatNotes, setFormatNotes] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.getDeadlines();
        if (!cancelled) setDeadlines(res);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const deadline = await api.createDeadline({
        venue_name: venueName,
        venue_type: venueType,
        submission_deadline: new Date(deadlineDate).toISOString(),
        venue_url: venueUrl || undefined,
        format_notes: formatNotes || undefined,
      });
      setDeadlines((prev) => [...prev, deadline]);
      setDialogOpen(false);
      setVenueName("");
      setDeadlineDate("");
      setVenueUrl("");
      setFormatNotes("");
      toast.success("Deadline created");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create deadline");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deleteDeadline(id);
      setDeadlines((prev) => prev.filter((d) => d.id !== id));
      toast.success("Deadline deleted");
    } catch {
      toast.error("Failed to delete deadline");
    }
  };

  const upcoming = deadlines.filter((d) => daysUntil(d.submission_deadline) >= 0);
  const past = deadlines.filter((d) => daysUntil(d.submission_deadline) < 0);

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Submission Deadlines</h2>
          <p className="text-muted-foreground">Track conference and journal deadlines</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger render={<Button />}>
            <Plus className="mr-2 h-4 w-4" />
            Add Deadline
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Submission Deadline</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="venueName">Venue Name</Label>
                <Input
                  id="venueName"
                  placeholder="IEEE ICBC 2026"
                  value={venueName}
                  onChange={(e) => setVenueName(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="venueType">Venue Type</Label>
                <Select value={venueType} onValueChange={(v) => v && setVenueType(v)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="conference">Conference</SelectItem>
                    <SelectItem value="journal">Journal</SelectItem>
                    <SelectItem value="workshop">Workshop</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="deadlineDate">Submission Deadline</Label>
                <Input
                  id="deadlineDate"
                  type="date"
                  value={deadlineDate}
                  onChange={(e) => setDeadlineDate(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="venueUrl">Venue URL (optional)</Label>
                <Input
                  id="venueUrl"
                  type="url"
                  placeholder="https://..."
                  value={venueUrl}
                  onChange={(e) => setVenueUrl(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="formatNotes">Format Notes (optional)</Label>
                <Textarea
                  id="formatNotes"
                  placeholder="IEEE 2-column, double-blind review..."
                  value={formatNotes}
                  onChange={(e) => setFormatNotes(e.target.value)}
                  rows={2}
                />
              </div>
              <Button type="submit" className="w-full" disabled={submitting}>
                {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Create Deadline
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Upcoming */}
      {upcoming.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
            Upcoming
          </h3>
          {upcoming
            .sort(
              (a, b) =>
                new Date(a.submission_deadline).getTime() -
                new Date(b.submission_deadline).getTime()
            )
            .map((deadline) => {
              const days = daysUntil(deadline.submission_deadline);
              const totalDays = 365;
              const progress = Math.max(0, Math.min(100, ((totalDays - days) / totalDays) * 100));

              return (
                <Card key={deadline.id}>
                  <CardContent className="pt-6">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 space-y-2">
                        <div className="flex items-center gap-2">
                          <Calendar className="h-4 w-4 text-muted-foreground" />
                          <h4 className="font-semibold">{deadline.venue_name}</h4>
                          <Badge variant="outline" className="text-xs">
                            {deadline.venue_type}
                          </Badge>
                          {deadline.venue_url && (
                            <a
                              href={deadline.venue_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-muted-foreground hover:text-foreground"
                            >
                              <ExternalLink className="h-3.5 w-3.5" />
                            </a>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground">
                          Deadline: {formatDate(deadline.submission_deadline)} &middot;{" "}
                          <span className="font-medium text-foreground">{days} days</span> remaining
                        </p>
                        {deadline.papers_count !== undefined && (
                          <p className="text-xs text-muted-foreground">
                            Papers targeting: {deadline.papers_count}
                          </p>
                        )}
                        <Progress value={progress} className="h-2 mt-2" />
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-muted-foreground hover:text-destructive"
                        onClick={() => handleDelete(deadline.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
        </div>
      )}

      {/* Past */}
      {past.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
            Past Deadlines
          </h3>
          {past.map((deadline) => (
            <Card key={deadline.id} className="opacity-60">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium">{deadline.venue_name}</span>
                    <span className="text-sm text-muted-foreground">
                      — {formatDate(deadline.submission_deadline)}
                    </span>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground hover:text-destructive"
                    onClick={() => handleDelete(deadline.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {deadlines.length === 0 && (
        <div className="text-center py-12">
          <Calendar className="mx-auto h-12 w-12 text-muted-foreground" />
          <h3 className="mt-4 text-lg font-semibold">No deadlines</h3>
          <p className="text-muted-foreground">Add a submission deadline to start tracking.</p>
        </div>
      )}
    </div>
  );
}

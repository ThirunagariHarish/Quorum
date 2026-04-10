"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import api, { type Paper } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { Download, Eye, FileText, Search } from "lucide-react";
import { toast } from "sonner";

const STATUS_BADGE: Record<string, string> = {
  draft: "bg-zinc-500/15 text-zinc-600 dark:text-zinc-400",
  in_review: "bg-yellow-500/15 text-yellow-700 dark:text-yellow-400",
  approved: "bg-green-500/15 text-green-700 dark:text-green-400",
  rejected: "bg-red-500/15 text-red-700 dark:text-red-400",
  published: "bg-blue-500/15 text-blue-700 dark:text-blue-400",
};

export default function FilesPage() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");

  useEffect(() => {
    const params: Record<string, string> = { per_page: "50" };
    if (statusFilter !== "all") params.status = statusFilter;
    if (typeFilter !== "all") params.paper_type = typeFilter;

    setLoading(true);
    api
      .getPapers(params)
      .then((res) => setPapers(res.items))
      .finally(() => setLoading(false));
  }, [statusFilter, typeFilter]);

  const filtered = papers.filter((p) =>
    p.title.toLowerCase().includes(search.toLowerCase())
  );

  const handleDownload = async (paper: Paper) => {
    try {
      const res = await api.downloadPaper(paper.id);
      window.open(res.download_url, "_blank");
    } catch {
      toast.error("Failed to download paper");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Files</h2>
        <p className="text-muted-foreground">Browse and manage generated papers</p>
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search papers..."
            className="pl-9"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select value={statusFilter} onValueChange={(v) => v && setStatusFilter(v)}>
          <SelectTrigger className="w-full sm:w-40">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="draft">Draft</SelectItem>
            <SelectItem value="in_review">In Review</SelectItem>
            <SelectItem value="approved">Approved</SelectItem>
            <SelectItem value="rejected">Rejected</SelectItem>
            <SelectItem value="published">Published</SelectItem>
          </SelectContent>
        </Select>
        <Select value={typeFilter} onValueChange={(v) => v && setTypeFilter(v)}>
          <SelectTrigger className="w-full sm:w-40">
            <SelectValue placeholder="Type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All types</SelectItem>
            <SelectItem value="ieee_full">IEEE Full</SelectItem>
            <SelectItem value="ieee_short">IEEE Short</SelectItem>
            <SelectItem value="workshop">Workshop</SelectItem>
            <SelectItem value="poster">Poster</SelectItem>
            <SelectItem value="blog">Blog</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Card>
        <CardContent className="pt-6">
          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Title</TableHead>
                  <TableHead className="w-28">Type</TableHead>
                  <TableHead className="w-28">Status</TableHead>
                  <TableHead className="w-32">Date</TableHead>
                  <TableHead className="w-24 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((paper) => (
                  <TableRow key={paper.id}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                        <span className="truncate max-w-[400px]">{paper.title}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs">
                        {paper.paper_type}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="secondary"
                        className={STATUS_BADGE[paper.status] || ""}
                      >
                        {paper.status.replace("_", " ")}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDate(paper.created_at)}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => handleDownload(paper)}
                        >
                          <Download className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <Eye className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
                {filtered.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-muted-foreground py-12">
                      {papers.length === 0
                        ? "No papers generated yet"
                        : "No papers match your search"}
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
